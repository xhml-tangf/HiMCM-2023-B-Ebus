"""Check saved solution artifacts separately from their constructors."""
from pathlib import Path
import json
import hashlib
import math
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/research_model'


def main():
    source=ROOT/'data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv'
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    audits=[]
    for name in ('central','slow_charge','winter_stress','capacity_stress'):
        schedule=json.loads((OUT/f'{name}_schedule.json').read_text())
        assert schedule['source_manifest_sha256']==sha
        assert schedule['outputs']['electric']['pattern_trips']+schedule['retained_trolley_pattern_trips']==495198
        assert schedule['outputs']['electric']['calendar_trip_instances']==schedule['outputs']['baseline']['calendar_trip_instances']
        for mode in ('electric','baseline'):
            duties=pd.read_csv(OUT/f'{name}_{mode}_duties.csv')
            assignments=pd.read_csv(OUT/f'{name}_{mode}_assignments.csv',dtype={'trip_id':str})
            assert not assignments.duplicated(['pattern_id','trip_id']).any()
            sizes=assignments.groupby(['pattern_id','duty_id']).size()
            actual=duties.set_index(['pattern_id','duty_id']).trip_count
            assert (sizes.sort_index()==actual.sort_index()).all()
            if mode=='electric':
                assert (duties.energy_kwh<=duties.usable_kwh+1e-6).all()
                assert np.allclose(duties.energy_kwh,(duties.charge_end_h-duties.return_h)*(.9*duties.charge_kw-duties.heat_kw))
            cal=pd.read_csv(OUT/f'{name}_{mode}_calendar.csv.gz')
            period=schedule['calendar_days']*24
            cal['s']=cal.depart_h%period
            cal['e']=cal.s+cal.ready_h-cal.depart_h
            for _,g in cal.sort_values('s').groupby('vehicle'):
                assert (g.e.to_numpy()[:-1]<=g.s.to_numpy()[1:]+1e-6).all()
                assert g.e.iloc[-1]<=g.s.iloc[0]+period+1e-6
            audits.append(dict(scenario=name,mode=mode,pattern_trips=len(assignments),
                               cyclic_assignments=len(cal),status='PASS'))
    solutions=0
    for name in ('central','slow_charge','winter_stress','capacity_stress','central_retrofit','central_high_cost'):
        result=json.loads((OUT/f'{name}_transition.json').read_text())
        for f in result['results']:
            baseline=pd.read_csv(OUT/f'{name}_{f["fuel_case"]}_baseline_ledger.csv')
            bcost=(baseline.cost_cad/1.03**(baseline.year-2023)).sum()
            bghg=baseline.ghg_t.sum()
            for sol in f['solutions']:
                assert sol['status']=='OPTIMAL_RESTRICTED_MASTER'
                # HiGHS may terminate on its absolute MIP tolerance even when
                # the requested relative tolerance is smaller. Retain and
                # check the ACTUAL returned gap; never replace it with zero.
                assert sol['mip_gap']<=1e-6
                frame=pd.read_csv(OUT/sol['ledger_file'])
                pcost=(frame.cost_cad/1.03**(frame.year-2023)).sum()
                pghg=frame.ghg_t.sum()
                assert math.isclose(pcost,sol['plan_pv_cad'],rel_tol=1e-10)
                assert math.isclose(bcost,sol['baseline_pv_cad'],rel_tol=1e-10)
                assert math.isclose(pghg,sol['plan_ghg_t'],rel_tol=1e-10)
                assert math.isclose(100*(bcost-pcost)/bcost,sol['economic_score_pct'],abs_tol=1e-8)
                assert math.isclose(100*(bghg-pghg)/bghg,sol['environmental_score_pct'],abs_tol=1e-8)
                assert frame[frame.year.eq(2033)].conventional_stock.sum()==0
                assert frame.groupby('year').acquired_electric.sum().max()<=result['annual_delivery_cap_assumption']
                assert sol['annual_inventory_and_spares_check']=='PASS'
                solutions+=1
    hashes={}
    for path in [ROOT/'src/solve_research_schedule.py',ROOT/'src/solve_research_transition.py',
                 ROOT/'src/price_catalog.py',ROOT/'src/price_index.py',
                 ROOT/'data/processed/canada_cpi_annual_2019_2025.csv',
                 ROOT/'data/processed/deck_shuttle_scenarios.csv',
                 ROOT/'data/processed/bchydro_2023_charging_tariffs.json',
                 ROOT/'results/vancouver_full_fleet_bound.json',
                 *OUT.glob('*schedule.json'),*OUT.glob('*transition.json')]:
        hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    result={'status':'PASS_RESEARCH_ARTIFACTS','dispatch_audits':audits,
            'independently_recomputed_master_solutions':solutions,'sha256':hashes,
            'qualification':'Tests certify the declared mathematical assumptions, not real land/grid/payload permissions.'}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'dispatch_cases':len(audits),'master_solutions':solutions}))


if __name__=='__main__':
    main()
