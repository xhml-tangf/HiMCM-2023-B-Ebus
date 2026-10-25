import pytest
from dataclasses import replace
from src.claude_impacts import Parameters,evaluate_impacts


def test_power_units_fleet_batteries_and_energy():
    p=Parameters()
    r=evaluate_impacts(10,12,500000,550000,2,3,p)
    assert p.B==540
    assert p.power_grid==480
    assert r['annual_grid_kwh']==pytest.approx(550000*1.6/.9)
    assert r['initial_embodied_electric_t']==pytest.approx(12*(70+540*58/1000))
    assert sum(x['battery_replacement']>0 for x in r['annual'])==1
    assert r['annual'][7]['battery_replacement']==pytest.approx(12*540*180*.97**8)


def test_grant_cap_and_npv_cash_reconciliation():
    r=evaluate_impacts(10,12,500000,550000,2,3)
    assert [g['phi'] for g in r['grants']]==[0,.25,.5]
    assert r['grants'][2]['grant']<=.5*r['capex_electric']
    assert r['grants'][2]['NPV']-r['grants'][0]['NPV']==pytest.approx(.5*r['grant_eligible_increment'])
    assert r['residual_diesel']>0 and r['residual_electric']>0


def test_negative_environmental_case_not_clipped():
    p=replace(Parameters(),grid=.8,diesel_ghg=.302)
    r=evaluate_impacts(10,20,100000,150000,2,5,p)
    assert r['ten_year_avoided_t']<0
    assert r['battery_carbon_payback_years'] is None
    assert r['phi_star']>.5 and not r['phi_star_within_cap']


def test_invalid_finance_parameters_fail():
    with pytest.raises(ValueError):
        Parameters(efficiency=0)
    with pytest.raises(ValueError):
        Parameters(vehicle_life=8)
