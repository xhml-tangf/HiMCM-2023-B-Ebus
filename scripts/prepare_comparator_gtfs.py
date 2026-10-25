"""Audit real GTFS schedules and build trip obligations for a stated week.

No modulo-24 clock, no invented departures, no distance-unit guesses.
London is the bus service touching NaPTAN 490 stops, not a fleet roster.
"""
from pathlib import Path
import sys,json,argparse,zipfile,hashlib,datetime,time
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.audit_gtfs_baseline import active_services,haversine_km
ROOT=Path(__file__).resolve().parents[1]

def seconds(s):
    a=s.str.split(':',expand=True).astype(float)
    return a[0]*3600+a[1]*60+a[2]

def time_string(s):
    s=int(s);return f'{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}'

def scalar_seconds(s):
    h,m,t=map(int,s.split(':'));return h*3600+m*60+t

def prepare(city,source,start):
    out=ROOT/'data/processed'/f'{city}_claude_gtfs';out.mkdir(parents=True,exist_ok=True)
    z=zipfile.ZipFile(source)
    def read(name):return pd.read_csv(z.open(name),dtype=str,keep_default_na=False)
    agency=read('agency.txt');routes=read('routes.txt');alltrips=read('trips.txt')
    cal=read('calendar.txt');exc=read('calendar_dates.txt')
    stops=read('stops.txt').set_index('stop_id')
    freq=read('frequencies.txt') if 'frequencies.txt' in z.namelist() else pd.DataFrame(columns=['trip_id'])
    dates=[datetime.date.fromisoformat(start)+datetime.timedelta(days=i) for i in range(7)]
    active={str(d):active_services(cal,exc,d) for d in dates}
    busroutes=routes[routes.route_type.isin(['3']+[str(i) for i in range(700,717)])]
    trips=alltrips[alltrips.route_id.isin(busroutes.route_id)&alltrips.service_id.isin(set().union(*active.values()))].copy()
    frequency=trips[trips.trip_id.isin(freq.trip_id)]
    global_frequency_count=len(frequency)
    if city=='london':
        # The historical archive is all Britain. A narrow first pass avoids
        # retaining millions of unrelated UK stop times in memory.
        local=set();all_ids=set(trips.trip_id)
        for chunk in pd.read_csv(z.open('stop_times.txt'),dtype=str,keep_default_na=False,
                                 usecols=['trip_id','stop_id'],chunksize=500000):
            local.update(chunk.loc[chunk.stop_id.str.startswith('490')&chunk.trip_id.isin(all_ids),'trip_id'])
        trips=trips[trips.trip_id.isin(local)];frequency=frequency[frequency.trip_id.isin(local)]
        print(city,'London geographic trip candidates',len(trips),'frequency templates',len(frequency),flush=True)
    exact_ids=set(freq.loc[freq.get('exact_times',pd.Series('',index=freq.index))=='1','trip_id'])
    unknown_ids=set(freq.trip_id)-exact_ids
    # GTFS exact_times=1 is a compact fixed schedule, so expand it faithfully.
    # Only nonexact headway service lacks fixed departure obligations.
    trips=trips[~trips.trip_id.isin(unknown_ids)]
    ids=set(trips.trip_id);parts=[];readrows=0
    cols=['trip_id','arrival_time','departure_time','stop_id','stop_sequence']
    for chunk in pd.read_csv(z.open('stop_times.txt'),dtype=str,keep_default_na=False,usecols=cols,chunksize=300000):
        readrows+=len(chunk);part=chunk[chunk.trip_id.isin(ids)]
        if len(part):parts.append(part)
        if readrows%3000000==0:print(city,'scanned',readrows,'stop times',flush=True)
    st=pd.concat(parts,ignore_index=True);del parts
    if city=='london':
        local=set(st.loc[st.stop_id.str.startswith('490'),'trip_id'])
        trips=trips[trips.trip_id.isin(local)];st=st[st.trip_id.isin(local)].copy()
    st['stop_sequence']=st.stop_sequence.astype(int)
    st=st.sort_values(['trip_id','stop_sequence']).reset_index(drop=True)
    assert not st.duplicated(['trip_id','stop_sequence']).any(),'duplicate trip stop sequence'
    st['lat']=pd.to_numeric(st.stop_id.map(stops.stop_lat));st['lon']=pd.to_numeric(st.stop_id.map(stops.stop_lon))
    assert np.isfinite(st[['lat','lon']]).all().all(),'missing stop coordinate'
    same=st.trip_id==st.trip_id.shift()
    st['segment_km']=np.where(same,haversine_km(st.lat.shift(),st.lon.shift(),st.lat,st.lon),0.)
    groups=st.groupby('trip_id',sort=False)
    first=groups.first();last=groups.last()
    f=trips.set_index('trip_id').join(first[['stop_id','departure_time']].rename(columns={'stop_id':'first_stop_id'}))
    f=f.join(last[['stop_id','arrival_time']].rename(columns={'stop_id':'last_stop_id'}))
    f['start_seconds']=seconds(f.departure_time);f['end_seconds']=seconds(f.arrival_time)
    f['distance_km_lower']=groups.segment_km.sum()
    f['distance_km_upper']=f.distance_km_lower*1.35
    f['distance_method']='1.35 x sum of great-circle distances between consecutive scheduled stops; scenario proxy, not a bound'
    # Preserve the full stop schedule for independent service checks, even though
    # EVSP treats an entire trip as one indivisible obligation.
    invalid=f[(f.end_seconds<=f.start_seconds)|(~np.isfinite(f.start_seconds))|(~np.isfinite(f.end_seconds))]
    invalid.reset_index().to_csv(out/'rejected_trips.csv',index=False)
    f=f.drop(invalid.index).reset_index()
    f['source_trip_id']=f.trip_id;f['frequency_offset_seconds']=0
    exact_frequency=freq[freq.trip_id.isin(set(f.trip_id)&exact_ids)]
    generated=[];generated_st=[]
    for r in exact_frequency.itertuples():
        base=f[f.trip_id==r.trip_id].iloc[0].to_dict()
        assert int(r.headway_secs)>0
        for departure in range(scalar_seconds(r.start_time),scalar_seconds(r.end_time),int(r.headway_secs)):
            delta=departure-base['start_seconds'];copy=base.copy();label=r.trip_id+'#F'+str(departure)
            copy.update(trip_id=label,start_seconds=float(departure),end_seconds=base['end_seconds']+delta,
                        departure_time=time_string(departure),arrival_time=time_string(base['end_seconds']+delta),frequency_offset_seconds=delta)
            generated.append(copy)
            stopcopy=st[st.trip_id==r.trip_id][cols].copy();stopcopy['trip_id']=label
            for column in ['arrival_time','departure_time']:
                stopcopy[column]=(seconds(stopcopy[column])+delta).map(time_string)
            generated_st.append(stopcopy)
    f=f[~f.trip_id.isin(exact_ids)]
    if generated:f=pd.concat([f,pd.DataFrame(generated)],ignore_index=True)
    st=st[~st.trip_id.isin(exact_ids|set(invalid.index))][cols]
    if generated_st:st=pd.concat([st,*generated_st],ignore_index=True)
    st.to_csv(out/'stop_times.csv.gz',index=False,compression='gzip')
    assert f.trip_id.is_unique and len(f)>0
    f['route_key']=f.route_id;f['route_short_name']=f.route_id.map(busroutes.set_index('route_id').route_short_name)
    endpoint_ids=sorted(set(f.first_stop_id)|set(f.last_stop_id));mapping={s:i for i,s in enumerate(endpoint_ids)}
    nodes=[dict(stop_id=s,name=stops.loc[s,'stop_name'],lat=float(stops.loc[s,'stop_lat']),lon=float(stops.loc[s,'stop_lon'])) for s in endpoint_ids]
    f['o']=f.first_stop_id.map(mapping);f['dst']=f.last_stop_id.map(mapping)
    f.to_csv(out/'trips.csv.gz',index=False,compression='gzip')
    cal.to_csv(out/'calendar.csv',index=False);exc.to_csv(out/'calendar_dates.csv',index=False)
    agency.to_csv(out/'agency.csv',index=False);busroutes.to_csv(out/'routes.csv',index=False)
    freq[freq.trip_id.isin(set(frequency.trip_id)&unknown_ids)].to_csv(out/'excluded_frequency_templates.csv',index=False)
    exact_frequency.to_csv(out/'expanded_exact_frequency_templates.csv',index=False)
    (out/'nodes.json').write_text(json.dumps(nodes,ensure_ascii=False,indent=2),encoding='utf-8')
    daily=[]
    for day,services in active.items():
        d=f[f.service_id.isin(services)]
        events=sorted([(s,1) for s in d.start_seconds]+[(e,-1) for e in d.end_seconds]);current=peak=0
        for _,change in events:current+=change;peak=max(peak,current)
        daily.append(dict(date=day,trips=len(d),routes=d.route_id.nunique(),PVR=peak,service_km=float(d.distance_km_upper.sum())))
    manifest=dict(city=city,source=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_calendar_start=cal.start_date.min(),source_calendar_end=cal.end_date.max(),
        feed_info=read('feed_info.txt').to_dict('records') if 'feed_info.txt' in z.namelist() else [],
        scope='CTA bus routes' if city=='chicago' else 'scheduled bus trips touching at least one London NaPTAN 490 stop; regional, not exact TfL contract fleet',
        week_start=start,unique_trips=len(f),endpoints=len(nodes),rejected_nonpositive_duration=len(invalid),
        frequency_templates_total_before_geographic_filter=global_frequency_count,
        frequency_templates_excluded_in_scope=len(set(frequency.trip_id)&unknown_ids),
        exact_frequency_templates_expanded=len(exact_frequency),exact_frequency_trips_generated=len(generated),
        frequency_policy='exact_times=1 expanded using source headways and stop offsets; nonexact templates retained separately without invented departures',
        distance_method=f.distance_method.iloc[0],daily=daily,
        year_warning='2026 methodological extension, not evidence of the 2023 network' if start.startswith('2026') else '2023 archive; retrospective acquisition in 2026')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('city',choices=['chicago','london']);p.add_argument('--source',required=True);p.add_argument('--start',required=True);a=p.parse_args()
    prepare(a.city,ROOT/a.source,a.start)
