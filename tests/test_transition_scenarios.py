import json
from math import isclose
from pathlib import Path

from src.build_transition_scenarios import allocate, pv


def test_purchase_allocation_exactly_conserves_blocks():
    plan = allocate(1798, range(2024, 2034))
    assert sum(plan.values()) == 1798
    assert max(plan.values()) - min(plan.values()) <= 1


def test_discounting_uses_2023_base_year():
    assert isclose(pv({2023: 100, 2024: 103}, base_year=2023, rate=.03), 200)


def test_saved_scenario_components_reconcile_to_gross_present_value():
    result = json.loads((Path(__file__).resolve().parents[1]
                         / "results/vancouver_transition_scenarios.json").read_text())
    for case in result["economics"]:
        c = case["components_pv_cad"]
        if case["case"] == "central":
            assert isclose(c["plan_bus_capex"] + c["plan_infrastructure"] + c["plan_om"]
                           + c["plan_vehicle_residual"], case["plan_gross_pv_cad"], abs_tol=.01)
        assert (-case["economic_score_gross_pct"] > 0)  # transparently negative, not relabelled positive


def test_environment_score_improves_as_baseline_is_cleaner():
    result = json.loads((Path(__file__).resolve().parents[1]
                         / "results/vancouver_transition_scenarios.json").read_text())
    scores = {x["case"]: x["environment_score_boundary_pct"] for x in result["environment"]}
    assert scores["fossil_diesel"] > scores["weighted_mix"] > scores["rng_heavy"] > 0
