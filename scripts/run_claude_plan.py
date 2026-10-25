"""Run the specification on existing Vancouver data; all outputs isolated."""
from pathlib import Path
import sys,json,time,argparse,math
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.claude_evsp import Instance,evaluate,select_stations,validate,diesel,pvr,block_pool,station_scores
from src.claude_data import load_data,day_frame,instance,source_manifest
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/claude_plan'


def save(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def summary(inst,sol,base=None):
    audit=validate(inst,sol.stations,sol.buses)
    audit.pop('sessions');audit.pop('duties')
    audit.update(PVR=pvr(inst),stations=list(sol.stations),repairs=sol.repairs,method=sol.method)
    if base is not None:
        db=Instance(math.inf,0,inst.tau,inst.w,inst.trips)
        dcheck=validate(db,[],base.buses)
        audit.update(N_d=base.N,diesel_deadhead_km=dcheck['deadhead_km'],
                     lower_bound_gap_pct=100*(sol.N-base.N)/base.N)
        assert sol.N>=base.N>=audit['PVR']
    return audit


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['main','patterns','sensitivity','roadmap','all'],default='all')
    parser.add_argument('--K',type=int,default=4)
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True,parents=True)
    frame,daily,cal,exc,nodes=load_data()
    # Highest published all-bus concurrency day; all 25 patterns subsequently checked.
    day=daily.sort_values(['peak_concurrent_trips_lower_bound','bus_trips'],ascending=False).iloc[0]['date']
    df=day_frame(frame,cal,exc,day)
    inst=instance(df,nodes)
    if args.stage in ['main','all']:
        began=time.perf_counter()
        print('main',day,inst.n,'trips',inst.m,'nodes',flush=True)
        base=diesel(inst);print('diesel exact',base.N,flush=True)
        pool=block_pool(inst,restarts=2)
        print('blocks',[len(b) for b in pool],flush=True)
        scores=station_scores(inst,pair_limit=50)
        candidates=sorted(range(inst.m),key=lambda c:(-scores[c],c))[:12]
        sol,trace=select_stations(inst,args.K,pool=pool,candidates=candidates,swaps=True)
        audit=summary(inst,sol,base)
        details=validate(inst,sol.stations,sol.buses)
        save(OUT/'vancouver_main.json',dict(date=day,**audit,trace=trace,candidates=candidates,
             selected_stops=[dict(node=c,**nodes[c]) for c in sol.stations],R=inst.R,T=inst.T,
             source_sha256=source_manifest(),elapsed_seconds=time.perf_counter()-began))
        save(OUT/'vancouver_duties.json',dict(date=day,trip_ids=inst.labels,stations=sol.stations,
             electric=sol.buses,diesel=base.buses,sessions=details['sessions']))
        df.to_csv(OUT/'vancouver_instance_trips.csv',index=False)
        save(OUT/'nodes.json',nodes)
        np.savez_compressed(OUT/'travel_matrices.npz',tau=inst.tau,w=inst.w)
        print('main done',audit['vehicles'],sol.stations,flush=True)
    main_data=json.loads((OUT/'vancouver_main.json').read_text(encoding='utf-8'))
    S=tuple(main_data['stations'])
    if args.stage in ['patterns','all']:
        rows=[]
        path=OUT/'patterns.json'
        if path.exists():
            rows=json.loads(path.read_text())['patterns']
        done={r['pattern_id'] for r in rows}
        for row in daily.drop_duplicates('pattern_id').itertuples():
            if int(row.pattern_id) in done:continue
            f=day_frame(frame,cal,exc,row.date);ii=instance(f,nodes)
            began=time.perf_counter();base=diesel(ii)
            sol=evaluate(ii,S,restarts=0)
            stats=summary(ii,sol,base)
            stats.update(pattern_id=int(row.pattern_id),date=row.date,
                         occurrence_days=int((daily.pattern_id==row.pattern_id).sum()),
                         elapsed_seconds=time.perf_counter()-began)
            rows.append(stats)
            save(OUT/f'duties_pattern_{row.pattern_id:02d}.json',dict(trip_ids=ii.labels,buses=sol.buses,stations=S))
            save(path,dict(patterns=rows))
            print('pattern',row.pattern_id,'N_d',base.N,'N_e',sol.N,'seconds',round(stats['elapsed_seconds'],1),flush=True)
        rows.sort(key=lambda r:r['pattern_id'])
        save(path,dict(patterns=rows,peak_N_e=max(r['vehicles'] for r in rows),
                      peak_N_d=max(r['N_d'] for r in rows),days=sum(r['occurrence_days'] for r in rows),
                      trip_instances=sum(r['trips']*r['occurrence_days'] for r in rows)))
    if args.stage in ['sensitivity','all']:
        rows=[];incumbents={}
        for R in (150.,225.,270.,350.,500.):
            ii=instance(df,nodes,R=R)
            pool=block_pool(ii)
            for T in (120.,60.,30.):
                jj=Instance(R,T,ii.tau,ii.w,ii.trips)
                sol=evaluate(jj,S,pool=pool)
                raw_N=sol.N
                for (oldR,oldT),old in incumbents.items():
                    if oldR<=R and oldT>=T and old.N<sol.N:
                        validate(jj,S,old.buses)
                        sol=old
                incumbents[(R,T)]=sol
                stats=summary(jj,sol);stats.update(R=R,T=T,raw_search_N=raw_N)
                rows.append(stats)
                print('R,T',R,T,sol.N,flush=True)
        extra=[]
        for name,kwargs in [('distance_lower',{'distance_bound':'lower'}),
                            ('road_stress',{'road_factor':1.6,'speed_kmh':25.})]:
            ii=instance(df,nodes,**kwargs);sol=evaluate(ii,S)
            extra.append(dict(case=name,**summary(ii,sol)))
        save(OUT/'sensitivity.json',dict(range_time=rows,other=extra,
             diesel_limit_N=main_data['N_d'],note='R=infinity solved by exact diesel matching. Fixed selected stations.'))
    if args.stage in ['roadmap','all']:
        # Route rankings are scenario productivity/cost proxies, without invented ages.
        ranks=[]
        for route,group in df.groupby('route_key'):
            ii=instance(group,nodes)
            nd=diesel(ii).N;sol=evaluate(ii,S,aware=False)
            km=float(ii.d.sum())
            # Emissions/km and positive extra capital common to homogeneous routes.
            score=km/max(1,sol.N)*(nd/max(1,sol.N))
            ranks.append(dict(route=str(route),N_d=nd,N_e=sol.N,km=km,score=score))
        ranks.sort(key=lambda r:(-r['score'],r['route']))
        ordered=[r['route'] for r in ranks];rows=[];stock=0
        for t,year in enumerate(range(2024,2034),1):
            selected=set(ordered[:math.ceil(len(ordered)*t/10)])
            f=df[df.route_key.isin(selected)]
            rest=df[~df.route_key.isin(selected)]
            ii=instance(f,nodes);sol=evaluate(ii,S,restarts=0)
            base=diesel(instance(rest,nodes))
            stats=summary(ii,sol);new=max(0,sol.N-stock);stock=max(stock,sol.N)
            stats.update(year=year,routes=sorted(selected),new_buses=new,purchased_stock=stock,
                         idle_stock=stock-sol.N,remaining_diesel=base.N,
                         new_stations=list(S) if t==1 else [])
            rows.append(stats)
            save(OUT/f'roadmap_duties_{year}.json',dict(trip_ids=ii.labels,buses=sol.buses,stations=S))
            print('roadmap',year,sol.N,base.N,flush=True)
        save(OUT/'roadmap_schedule.json',dict(date=day,route_ranking=ranks,annual=rows,
             scope='Representative-day nested route deployment; all 25 full-conversion patterns checked separately.',
             budget_status='Required spending calculated downstream, not an externally funded budget.',
             age_status='Route/vehicle ages missing: no claim of oldest-first implementation.'))


if __name__=='__main__':main()
