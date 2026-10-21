"""Adversarial checks for the conditional dispatch and annual master."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from src.solve_research_schedule import periodic_color, check_periodic_intervals, construct_pattern
from src.solve_research_transition import prepare, ledger, solve_options

ROOT=Path(__file__).resolve().parents[1]


def test_circular_coloring_catches_last_to_first_conflict():
    # Night duty overlaps the next cycle's first duty: cannot share a bus.
    c,n=periodic_color([23,1,4],[26,3,6],24)
    assert n==2
    assert c[0]!=c[1]
    with pytest.raises(ValueError,match='collision'):
        check_periodic_intervals([1,23],[3,26],[0,0],24)


def test_wrap_resource_can_be_reused_inside_free_gap():
    c,n=periodic_color([23,4,10],[26,6,12],24)
    assert n==1
    assert len(set(c))==1


def test_long_interval_rejected_instead_of_truncated():
    with pytest.raises(ValueError):
        periodic_color([0],[25],24)


def test_master_cannot_hide_procurement_shortfall():
    # Two packages each require two buses; one available year holds three.
    result=solve_options([1.,1.],[1.,1.],[0,1],[[2,0,0,0],[2,0,0,0]],3,.5)
    assert result['status']=='INFEASIBLE'


def test_master_preserves_package_and_year_capacity():
    result=solve_options([4.,2.,4.,3.],[1.,3.,1.,3.],[0,0,1,1],
                         [[2,0,0,0],[0,2,0,0],[2,0,0,0],[0,2,0,0]],2,0.)
    assert result['status']=='OPTIMAL_RESTRICTED_MASTER'
    assert result['annual_electric_purchases']==[2,2,0,0]


def central_package():
    d=json.loads((ROOT/'results/research_model/central_schedule.json').read_text())
    return next(p for p in prepare(d) if p['cls']=='shuttle')


def test_five_year_shuttle_bridge_renewal_is_not_omitted():
    p=central_package()
    rows=ledger(p,2033,.302)
    assert sum(r['acquired_conventional'] for r in rows)>p['initial']
    assert rows[-1]['conventional_stock']==0
    assert rows[-1]['electric_stock']==p['ev']['fleet_with_15pct_spare']
    assert sum(r['infrastructure_capex_cad']>0 for r in rows)==6
    assert all(r['infrastructure_capex_cad']==0 for r in rows if r['year']>=2033)


def test_new_shuttle_gets_five_full_years_before_replacement():
    p=copy.deepcopy(central_package())
    p['initial']=5;p['baseline_fleet']=5;p['existing_beb']=0
    rows=ledger(p,None,.302)
    assert [r['acquired_conventional'] for r in rows]==[1]*10


def test_higher_grid_factor_changes_environment_not_dispatch():
    p=central_package()
    clean=ledger(p,2030,.302,grid=.0113)
    dirty=ledger(p,2030,.302,grid=.6)
    assert sum(r['ghg_t'] for r in dirty)>sum(r['ghg_t'] for r in clean)
    assert [r['acquired_electric'] for r in dirty]==[r['acquired_electric'] for r in clean]
    assert sum(r['cost_cad'] for r in dirty)==pytest.approx(sum(r['cost_cad'] for r in clean))


def test_resale_sensitivity_cannot_credit_initial_purchase_again():
    p=central_package()
    rows=ledger(p,2030,.302,resale=0.)
    assert all(r['sale_credit_cad']==0 for r in rows)
    assert sum(r['acquired_electric'] for r in rows)==p['ev']['fleet_with_15pct_spare']
    assert rows[-1]['terminal_credit_cad']<0


def test_all_patterns_exact_coverage_and_calendar_cycle_checked():
    d=json.loads((ROOT/'results/research_model/central_schedule.json').read_text())
    e=d['outputs']['electric'];b=d['outputs']['baseline']
    assert d['service_patterns']==25 and d['calendar_days']==119
    assert e['pattern_trips']+d['retained_trolley_pattern_trips']==495198
    assert e['pattern_trips']==b['pattern_trips']
    assert e['calendar_trip_instances']==b['calendar_trip_instances']
    assert e['cyclic_vehicle_collision_check']=='PASS'
    assert e['independent_ledger_max_error']<1e-5
    assert e['fleet_with_spares']>=e['active_buses']


def test_canonical_policy_and_full_life_recommendation_are_recorded():
    schedule=json.loads((ROOT/'results/research_model/central_schedule.json').read_text())
    assert all(p['fleet_with_15pct_spare'] >= p['active_buses'] for p in schedule['outputs']['electric']['packages'])
    transition=json.loads((ROOT/'results/research_model/central_transition.json').read_text())
    assert transition['parameter_overrides']=={
        'infra_multiplier': 0.5, 'infra_carbon_multiplier': 0.3,
        'annual_energy_multiplier': 0.8}
    primary=next(x for x in transition['results'] if x['fuel_case']=='renewable_mix')
    rec=primary['recommended']
    assert rec['full_life_plan_t'] < rec['full_life_baseline_t']
    assert rec['full_life_environment_score_pct'] > 0
    assert rec['zero_conventional_2033_check']=='PASS'
    assert max(rec['annual_electric_purchases']) <= transition['annual_delivery_cap_assumption']
