"""Read persisted schedules back, rebuilding each dated trip set from GTFS manifest."""
from pathlib import Path
import sys,json,math,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.run_comparator_plan import load,read,save
from src.claude_data import instance,day_frame
from src.claude_evsp import validate,Instance
ROOT=Path(__file__).resolve().parents[1]

def close(a,b):assert abs(a-b)<=max(1e-5,abs(b)*1e-8),(a,b)
def verify(city):
    f,cal,exc,nodes,manifest=load(city);out=ROOT/'results/claude_plan'/city
    assert hashlib.sha256((ROOT/manifest['source']).read_bytes()).hexdigest()==manifest['sha256']
    main=read(out/'main.json');S=main['stations'];count=0
    day_rows=read(out/'days.json')['days'];expected_dates=[d['date'] for d in manifest['daily']]
    assert [r['date'] for r in day_rows]==expected_dates,('incomplete or misordered dates',expected_dates)
    for row in day_rows:
        d=read(out/f'duties_{row["date"]}.json');fi=day_frame(f,cal,exc,row['date']);ii=instance(fi,nodes)
        assert ii.labels==d['trip_ids'] and d['stations']==S
        a=validate(ii,S,d['electric']);b=validate(Instance(math.inf,0,ii.tau,ii.w,ii.trips),[],d['diesel'])
        for k in ['vehicles','trips','service_km','deadhead_km','daytime_charge_count','daytime_replenished_range_km','overnight_replenished_range_km']:close(a[k],row[k])
        assert b['vehicles']==row['N_d'];close(b['deadhead_km'],row['diesel_deadhead_km'])
        count+=ii.n
    full=day_frame(f,cal,exc,main['date']);previous=set();stock=0;stage_trips=0
    sensitivity=read(out/'sensitivity.json')['cases']
    assert {(r['R'],r['T']) for r in sensitivity}=={(R,T) for R in (180.,270.,400.) for T in (90.,60.,30.)}
    for row in sensitivity:
        ii=instance(full,nodes,R=row['R'],T=row['T'])
        d=read(out/f'sensitivity_duties_{int(row["R"])}_{int(row["T"])}.json')
        a=validate(ii,S,d['buses']);assert a['vehicles']==row['vehicles']
        for old in sensitivity:
            if old['R']<=row['R'] and old['T']>=row['T']:assert row['vehicles']<=old['vehicles']
    annual=read(out/'roadmap.json')['annual']
    assert [r['year'] for r in annual]==list(range(2024,2034)),'incomplete annual stages'
    for row in annual:
        routes=set(row['routes']);assert previous<=routes;previous=routes
        ii=instance(full[full.route_key.isin(routes)],nodes);d=read(out/f'roadmap_duties_{row["year"]}.json')
        assert d['trip_ids']==ii.labels and d['stations']==S
        a=validate(ii,S,d['buses']);assert a['vehicles']==row['vehicles']
        assert row['new_buses']==max(0,row['vehicles']-stock);stock=max(stock,row['vehicles']);stage_trips+=ii.n
    assert previous==set(full.route_key)
    assert read(out/'roadmap.json')['annual'][-1]['remaining_diesel']==0
    budget=read(out/'roadmap_budget.json')['annual']
    assert [r['year'] for r in budget]==list(range(2024,2034)),'incomplete budget stages'
    for row in budget:
        assert 0<=row['grant50']<=.5*row['investment'];close(row['self_funded50']+row['grant50'],row['investment'])
    for phi in (0,25,50):
        balance=0.
        for row in budget:
            balance+=row[f'net_cash_grant{phi}']
            close(row[f'cumulative_cash_grant{phi}'],balance)
    impacts=read(out/'impacts.json')['standardized_transfer']
    for g in impacts['grants']:close(g['NPV'],impacts['pv_diesel']-impacts['pv_electric_gross']+g['grant'])
    result=dict(status='PASS',city=city,week_trip_instances=count,annual_stage_trip_instances=stage_trips,
        verified_day_schedules=len(day_rows),verified_annual_stages=len(annual),verified_sensitivity_schedules=len(sensitivity),source_hash_verified=True,energy_closure=True,
        boundary='Independent token replay; conditional travel/distance/charging assumptions; not repeated-day depot closure.')
    save(out/'verification.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':
    for city in sys.argv[1:] or ['chicago','london']:verify(city)
