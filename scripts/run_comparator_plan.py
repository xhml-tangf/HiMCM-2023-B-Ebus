"""Same EVSP engine on acquired comparator timetables; restartable stages."""
from pathlib import Path
from dataclasses import replace
import sys,json,time,math,argparse
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.claude_data import day_frame,instance as data_instance
from src.claude_evsp import diesel,validate,pvr,evaluate,block_pool,station_scores,select_stations,Instance
from src.claude_impacts import Parameters,evaluate_impacts
ROOT=Path(__file__).resolve().parents[1]

def instance(*args,**kwargs):
    result=data_instance(*args,**kwargs)
    result.sparse_links=result.n>30000
    return result

def save(p,j):p.write_text(json.dumps(j,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def load(city):
    p=ROOT/'data/processed'/f'{city}_claude_gtfs'
    f=pd.read_csv(p/'trips.csv.gz',dtype={'trip_id':str,'service_id':str,'route_id':str,'route_key':str},low_memory=False)
    return f,pd.read_csv(p/'calendar.csv',dtype=str),pd.read_csv(p/'calendar_dates.csv',dtype=str),read(p/'nodes.json'),read(p/'manifest.json')
def stats(ii,sol,base=None):
    a=validate(ii,sol.stations,sol.buses)
    for k in ['sessions','duties']:a.pop(k)
    a.update(PVR=pvr(ii),stations=list(sol.stations),repairs=sol.repairs,method=sol.method,
             daytime_grid_kwh=a['daytime_replenished_range_km']*1.6/.9,
             overnight_grid_kwh=a['overnight_replenished_range_km']*1.6/.9)
    if base is not None:
        di=Instance(math.inf,0,ii.tau,ii.w,ii.trips)
        a['N_d']=base.N;a['diesel_deadhead_km']=validate(di,[],base.buses)['deadhead_km']
        assert sol.N>=base.N>=a['PVR']
    return a

def main(city,stage):
    f,cal,exc,nodes,manifest=load(city);out=ROOT/'results/claude_plan'/city;out.mkdir(exist_ok=True)
    day=max(manifest['daily'],key=lambda r:(r['PVR'],r['trips']))['date']
    frame=day_frame(f,cal,exc,day);ii=instance(frame,nodes)
    if stage in ['main','all'] and not (out/'main.json').exists():
        started=time.perf_counter();print(city,day,ii.n,'trips',ii.m,'nodes',flush=True)
        base=diesel(ii);print(city,'exact diesel',base.N,flush=True)
        pool=block_pool(ii)
        # Bounded candidate screening affects quality, never feasibility or Nd.
        scores=station_scores(ii,pair_limit=20)
        candidates=sorted(range(ii.m),key=lambda c:(-scores[c],c))[:8]
        print(city,'blocks',[len(b) for b in pool],'candidates',candidates,flush=True)
        sol,trace=select_stations(ii,4,pool=pool,candidates=candidates,swaps=False)
        a=stats(ii,sol,base)
        save(out/'duties_main.json',dict(trip_ids=ii.labels,electric=sol.buses,diesel=base.buses,stations=sol.stations))
        save(out/'main.json',dict(date=day,**a,trace=trace,candidates=candidates,source_manifest=manifest,
             selected_stops=[dict(node=c,**nodes[c]) for c in sol.stations],R=ii.R,T=ii.T,
             elapsed_seconds=time.perf_counter()-started,
             search='same solver; top 8 candidates from 20-successor screening; K<=4; no station swaps'))
        print(city,'electric',sol.N,sol.stations,flush=True)
    m=read(out/'main.json');S=m['stations']
    if stage in ['days','all']:
        rows=read(out/'days.json')['days'] if (out/'days.json').exists() else []
        for d in manifest['daily']:
            if any(r['date']==d['date'] for r in rows):continue
            if d['date']==day:
                r={k:v for k,v in m.items() if k not in ['trace','candidates','selected_stops','source_manifest']}
                saved=read(out/'duties_main.json')
            else:
                fi=day_frame(f,cal,exc,d['date']);ij=instance(fi,nodes);base=diesel(ij)
                sol=evaluate(ij,S);r=dict(date=d['date'],**stats(ij,sol,base))
                saved=dict(trip_ids=ij.labels,electric=sol.buses,diesel=base.buses,stations=S)
            save(out/f'duties_{d["date"]}.json',saved);rows.append(r)
            save(out/'days.json',dict(days=rows));print(city,'day',d['date'],r['N_d'],r['vehicles'],flush=True)
    if stage in ['sensitivity','all']:
        rows=[];incumbents={}
        for R in (180.,270.,400.):
            ir=instance(frame,nodes,R=R);pool=block_pool(ir)
            for T in (90.,60.,30.):
                it=Instance(R,T,ir.tau,ir.w,ir.trips)
                it.sparse_links=ir.sparse_links
                sol=evaluate(it,S,pool=pool);raw=sol.N
                for (r,t),old in incumbents.items():
                    if r<=R and t>=T and old.N<sol.N:validate(it,S,old.buses);sol=old
                incumbents[(R,T)]=sol
                rows.append(dict(R=R,T=T,raw_search_N=raw,**stats(it,sol)));save(out/'sensitivity.json',dict(cases=rows))
                save(out/f'sensitivity_duties_{int(R)}_{int(T)}.json',dict(R=R,T=T,buses=sol.buses,stations=S))
                print(city,'sensitivity',R,T,sol.N,flush=True)
    if stage in ['roadmap','all']:
        # A transparent route score, not an unsupported local cost/age ranking.
        route_scores=[]
        for route,g in frame.groupby('route_key',sort=True):
            ir=instance(g,nodes);nd=diesel(ir).N;ne=evaluate(ir,S).N
            route_scores.append(dict(route=str(route),score=float(g.distance_km_upper.sum()*nd/ne**2),Nd=nd,Ne=ne))
        route_scores.sort(key=lambda r:(-r['score'],r['route']))
        save(out/'route_scores.json',route_scores)
        rows=read(out/'roadmap.json')['annual'] if (out/'roadmap.json').exists() else []
        for t in range(1,11):
            year=2023+t
            if any(r['year']==year for r in rows):continue
            selected=[r['route'] for r in route_scores[:math.ceil(len(route_scores)*t/10)]]
            part=frame[frame.route_key.isin(selected)];ir=instance(part,nodes)
            sol=evaluate(ir,S);remaining=diesel(instance(frame[~frame.route_key.isin(selected)],nodes)).N
            stock=max((r['purchased_stock'] for r in rows),default=0)
            r=dict(year=year,routes=selected,**stats(ir,sol),remaining_diesel=remaining,
                   new_buses=max(0,sol.N-stock),purchased_stock=max(sol.N,stock))
            rows.append(r);save(out/'roadmap.json',dict(date=day,annual=rows,scope='2024-2033 counterfactual; no supplied hard budget or route-age assignment'))
            save(out/f'roadmap_duties_{year}.json',dict(trip_ids=ir.labels,buses=sol.buses,stations=S))
            print(city,'roadmap',year,sol.N,remaining,flush=True)
    if stage in ['impacts','all']:
        days=read(out/'days.json')['days'];p=Parameters()
        expected={d['date'] for d in manifest['daily']};actual={d['date'] for d in days}
        assert actual==expected,(city,'incomplete dates',sorted(expected-actual),sorted(actual-expected))
        roadmap=read(out/'roadmap.json')['annual']
        assert [r['year'] for r in roadmap]==list(range(2024,2034)),(city,'incomplete roadmap')
        assert set(roadmap[-1]['routes'])==set(frame.route_key),'final route stage not complete'
        annual=lambda key:sum(r[key] for r in days)*365/len(days)
        peaks={str(c):max(r['charger_peak_by_node'].get(str(c),0) for r in days) for c in S}
        args=dict(Nd=max(r['N_d'] for r in days),Ne=max(r['vehicles'] for r in days),
                  Dd=annual('service_km')+annual('diesel_deadhead_km'),De=annual('service_km')+annual('deadhead_km'),
                  stations=len(S),plugs=sum(peaks.values()))
        central=evaluate_impacts(**args,p=p)
        grid_cases=[dict(rate=r,result=evaluate_impacts(**args,p=p,grid_decline=r)) for r in (0.,.03,.05)]
        air=pd.read_csv(ROOT/'data/processed/transit_air_quality_factors_2023.csv')
        pollution=[]
        for pollutant in ['NOx','PM2.5']:
            factors=air[(air.fuel=='diesel')&(air.pollutant==pollutant)].g_per_km
            pollution.append(dict(pollutant=pollutant,annual_avoided_t_low=args['Dd']*factors.min()/1e6,
                annual_avoided_t_high=args['Dd']*factors.max()/1e6,ten_year_avoided_t_low=args['Dd']*factors.min()*10/1e6,
                ten_year_avoided_t_high=args['Dd']*factors.max()*10/1e6,note='Transferred tailpipe factors; no non-exhaust benefit claimed.'))
        save(out/'impacts.json',dict(standardized_transfer=central,strict_zero_source=evaluate_impacts(**args,p=replace(p,grid=0.)),
            boundary='Common Vancouver 2023-CAD technical/cost parameters, not local tariffs, local grid intensity, or a city investment forecast. One observed week annualized by 365/7.',
            annual_service_km=annual('service_km'),peaks=peaks,grid_decline_cases=grid_cases,pollution=pollution))
        budget=[];previous_d=m['N_d'];cum=0.;cum_ghg=0.;cum_cash={0.:0.,.25:0.,.5:0.}
        for row in roadmap:
            t=row['year']-2024;bp=p.battery_price*(1-p.battery_decline)**t
            earlier=next((x for x in budget if x['year']==row['year']-p.battery_life),None)
            new=row['new_buses']
            if t==9:new+=max(0,args['Ne']-row['purchased_stock'])
            investment=new*(p.body_price+p.B*bp)+(central['infrastructure'] if t==0 else 0.)+(earlier['new_buses']*p.B*bp if earlier else 0.)
            displaced=max(0,previous_d-row['remaining_diesel']);previous_d=row['remaining_diesel']
            eligible=max(0,investment-displaced*p.diesel_bus_price);cum+=investment
            electric_km=(row['service_km']+row['deadhead_km'])*365
            displaced_diesel_km=row['service_km']*365
            operating_avoided=(displaced_diesel_km*p.diesel_ghg-electric_km*p.epsilon/p.efficiency*p.grid)/1000
            replacement_ghg=(earlier['new_buses']*p.B*p.battery_ghg/1000 if earlier else 0.)
            embodied=new*(p.body_ghg_t+p.B*p.battery_ghg/1000)
            cum_ghg+=operating_avoided-embodied-replacement_ghg
            grid_kwh=electric_km*p.epsilon/p.efficiency
            diesel_op_avoided=displaced_diesel_km*(p.litres_km*p.diesel_price+p.diesel_maintenance)
            electric_op=grid_kwh*p.electricity+electric_km*p.electric_maintenance+central['infrastructure']*p.station_maintenance_fraction
            op_saving=diesel_op_avoided-electric_op
            diesel_purchase_avoided=displaced*p.diesel_bus_price
            cash={phi:op_saving+diesel_purchase_avoided-investment+phi*eligible for phi in (0.,.25,.5)}
            for phi in cum_cash:cum_cash[phi]+=cash[phi]
            budget.append(dict(year=row['year'],new_buses=new,active_electric=row['vehicles'],diesel=row['remaining_diesel'],
                stations=len(S),routes=len(row['routes']),investment=investment,eligible=eligible,grant0=0.,grant25=.25*eligible,grant50=.5*eligible,
                self_funded50=investment-.5*eligible,cumulative_investment=cum,battery_replacement=(earlier['new_buses']*p.B*bp if earlier else 0.),
                grid_kwh=grid_kwh,diesel_operating_avoided=diesel_op_avoided,electric_operating_cost=electric_op,
                operating_saving=op_saving,diesel_purchase_avoided=diesel_purchase_avoided,
                net_cash_grant0=cash[0.],net_cash_grant25=cash[.25],net_cash_grant50=cash[.5],
                cumulative_cash_grant0=cum_cash[0.],cumulative_cash_grant25=cum_cash[.25],cumulative_cash_grant50=cum_cash[.5],
                cumulative_partial_avoided_t=cum_ghg))
        save(out/'roadmap_budget.json',dict(annual=budget,
            scope='Required-budget transfer in common 2023 CAD; not a local appropriation or commissioning commitment',
            ghg_boundary='Partial staged operating-minus-new-production ledger; no old-fleet manufacture credit or unknown diesel detours.'))
        pd.DataFrame(budget).to_csv(out/'roadmap_budget.csv',index=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('city',choices=['chicago','london']);p.add_argument('--stage',default='all',choices=['main','days','sensitivity','roadmap','impacts','all']);a=p.parse_args()
    main(a.city,a.stage)
