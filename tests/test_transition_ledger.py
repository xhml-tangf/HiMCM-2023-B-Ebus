from math import isclose

from src.transition_ledger import (READINESS_2024_33, service_ledger,
                                   operating_costs, use_emissions)


def test_no_conversion_keeps_baseline_use_emissions_and_costs():
    ledger = service_ledger(1000, [0] * 10)
    use = use_emissions(ledger, 1.58)
    assert use['baseline_operating_t'] == use['plan_operating_t']
    assert use['baseline_maintenance_t'] == use['plan_maintenance_t']
    baseline, plan = operating_costs(ledger, 2.77, 2.28)
    assert baseline == plan


def test_immediate_conversion_has_no_conventional_use():
    ledger = service_ledger(1000, [1] * 10)
    use = use_emissions(ledger, 1.58)
    assert isclose(use['plan_operating_t'], .19)
    assert isclose(use['plan_maintenance_t'], .675)


def test_ramp_conserves_km_and_matches_independent_arithmetic():
    ledger = service_ledger(1000, [i / 10 for i in range(1, 11)])
    assert all(isclose(r['electric_km'] + r['conventional_km'], 1000) for r in ledger)
    assert isclose(sum(r['electric_km'] for r in ledger), 5500)
    assert isclose(sum(r['conventional_km'] for r in ledger), 4500)
    use = use_emissions(ledger, 1.58)
    assert isclose(use['plan_operating_t'], 7.2145)
    assert isclose(use['plan_maintenance_t'], .60705)
    _, plan = operating_costs(ledger, 2.77, 2.28)
    assert isclose(sum(plan.values()), 25005)


def test_default_ramp_is_bounded_by_site_readiness():
    ledger = service_ledger(1000)
    assert [r['electric_share'] for r in ledger] == list(READINESS_2024_33)
    assert all(r['electric_share'] == 0 for r in ledger[:6])
    assert ledger[-1]['electric_share'] == 1


def test_low_carbon_case_can_reverse_with_one_replacement_cohort():
    # Independent published-audit counterexample; no all-electric year-1 shortcut.
    km = 88786898.9817
    use = use_emissions(service_ledger(km, [i / 10 for i in range(1, 11)]), .302)
    baseline = 816 * 11429 * 6.6 / 1000 + use['baseline_operating_t'] + use['baseline_maintenance_t']
    plan = 1612 * (14880 * 6.6 + 335 * 58) / 1000 + use['plan_operating_t'] + use['plan_maintenance_t']
    assert 0 < baseline - plan < 162 * 335 * 58 / 1000
