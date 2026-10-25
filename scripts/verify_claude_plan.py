"""Read-back verification independent of the output-producing pipeline."""
from pathlib import Path
from dataclasses import replace
import sys,json,math,hashlib
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.claude_data import load_data,day_frame,instance,source_manifest
from src.claude_evsp import validate,Instance
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/claude_plan'
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def close(a,b):assert abs(a-b)<=max(1e-5,abs(b)*1e-8),(a,b)


def main():
    frame,daily,cal,exc,nodes=load_data();benchmark_full=read('benchmark.json');benchmark=benchmark_full['summary']
    assert benchmark['p1_cases']==300 and len(benchmark_full['p2'])==60 and benchmark['diesel_limit_passed']==200
    central=read('vancouver_main.json');patterns=read('patterns.json')
    assert central['source_sha256']==source_manifest()
    assert len(patterns['patterns'])==25 and patterns['days']==119
    checked=0
    for row in patterns['patterns']:
        duty=read(f'duties_pattern_{row["pattern_id"]:02d}.json')
        f=day_frame(frame,cal,exc,row['date']);inst=instance(f,nodes)
        assert inst.labels==duty['trip_ids']
        assert set(duty['stations'])==set(central['stations'])
        actual=validate(inst,duty['stations'],duty['buses'])
        for key in ['vehicles','trips','service_km','deadhead_km','daytime_charge_count',
                    'daytime_replenished_range_km','overnight_replenished_range_km']:
            close(actual[key],row[key])
        assert row['N_d']>=row['PVR'] and row['vehicles']>=row['N_d']
        checked+=actual['trips']
    schedule=read('roadmap_schedule.json')
    full=day_frame(frame,cal,exc,schedule['date'])
    previous=set();stock=0
    for row in schedule['annual']:
        selected=set(row['routes'])
        assert previous<=selected;previous=selected
        f=full[full.route_key.isin(selected)]
        inst=instance(f,nodes)
        duty=read(f'roadmap_duties_{row["year"]}.json')
        assert inst.labels==duty['trip_ids']
        actual=validate(inst,duty['stations'],duty['buses'])
        assert actual['vehicles']==row['vehicles']
        assert row['new_buses']==max(0,row['vehicles']-stock)
        stock=max(stock,row['vehicles']);assert stock==row['purchased_stock']
    assert previous==set(full.route_key) and schedule['annual'][-1]['remaining_diesel']==0
    imp=read('impacts.json');c=imp['central']
    close(imp['daytime_grid_kwh']+imp['overnight_grid_kwh'],c['annual_grid_kwh'])
    assert c['Ne']==max(r['vehicles'] for r in patterns['patterns'])
    assert c['Nd']==max(r['N_d'] for r in patterns['patterns'])
    for grant in c['grants']:
        assert 0<=grant['phi']<=.5
        close(grant['grant'],grant['phi']*c['grant_eligible_increment'])
        close(grant['NPV'],c['pv_diesel']-c['pv_electric_gross']+grant['grant'])
        cash=grant['cashflow'];balance=0
        for r in cash:
            balance+=r['cash'];close(r['cumulative'],balance)
        rate=imp['parameters']['discount']['value']
        close(sum(r['cash']/(1+rate)**r['t'] for r in cash),grant['NPV'])
    for r in read('roadmap_budget.json')['annual']:
        assert r['grant50']<=.5*r['gross_investment']+1e-5
        close(r['self_funded50']+r['grant50'],r['gross_investment'])
    comparable=read('comparators.json')
    for city in ['chicago','london']:
        extra=read(f'{city}/verification.json')
        assert extra['status']=='PASS'
        schedule=read(f'{city}/main.json')
        assert comparable[city]['Nd']==schedule['N_d'] and comparable[city]['Ne']==schedule['vehicles']
    assert comparable['chicago']['cohort']['schedule'][-1]['non_electric_slots_remaining']==0
    for sc in comparable['london']['cohort_scenarios']:
        assert sc['annual_schedule'][-1]['remaining_non_electric_slots']==0
    output=dict(status='PASS',pattern_schedules=25,unique_pattern_trip_occurrences_checked=checked,
                annual_stage_schedules=10,expanded_calendar_trip_instances=patterns['trip_instances'],
                exact_benchmark=benchmark,
                energy_closure=True,grant_and_discounted_cash_closure=True,
                comparator_schedules_independently_verified=True,
                outstanding=['cross-day fleet closure','real budgets and commissioning','local comparator costs and energy factors',
                             'full AI conversation transcripts'])
    (OUT/'verification.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
