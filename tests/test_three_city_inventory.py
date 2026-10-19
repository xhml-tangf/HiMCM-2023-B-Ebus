import json
from pathlib import Path

import pandas as pd

from src.make_three_city_roadmap import (build_cta_age_model,
                                         build_cta_age_scenario,
                                         load_cta_age_cohorts)


ROOT = Path(__file__).resolve().parents[1]


def test_three_city_inventory_endpoints_are_explicit():
    result = json.loads((ROOT / "results/three_city_roadmap.json").read_text())
    rows = pd.read_csv(ROOT / "data/processed/three_city_roadmap_2023.csv")
    assert len(rows) == 10
    assert rows.vancouver_beb_purchases.sum() == 1647
    assert rows.vancouver_electric_vehicle_purchases.sum() == 1909
    assert rows.vancouver_conventional_stock_end.iloc[-1] == 0
    assert rows.vancouver_electric_stock_end.iloc[-1] == 1927
    assert rows.chicago_non_electric_remaining.iloc[-1] == 0
    assert rows.london_non_electric_remaining.iloc[-1] == 0
    assert result["vancouver"]["endpoint"]["conventional_stock"] == 0
    assert result["endpoint_2033"] == {
        "vancouver_conventional": 0,
        "chicago_conventional": 0,
        "london_conventional": 0,
    }


def test_cta_age_bins_are_exhaustive_and_type_compatible():
    cohorts = load_cta_age_cohorts()
    assert sum(row["vehicles"] for row in cohorts) == 1875
    assert sum(row["vehicles"] for row in cohorts
               if row["vehicle_type"] == "Bus") == 1576
    assert sum(row["vehicles"] for row in cohorts
               if row["vehicle_type"] == "Articulated Bus") == 299


def test_cta_2024_hard_deadline_shortfalls_are_explicit():
    model = build_cta_age_model(load_cta_age_cohorts())
    assert model["2024_due_by_life_cap"] == {17: 539, 14: 1056, 12: 1086}
    assert model["2024_shortfall_by_life_cap"] == {17: 354, 14: 871, 12: 901}
    assert model["all_selected_life_caps_feasible_at_185"] is False
    assert model["status"] == "HARD_AGE_STRESS_INFEASIBLE_AT_185_ANNUAL_PURCHASES"


def test_cta_age_model_does_not_erase_missed_deadlines_after_backlog_clears():
    cohorts = load_cta_age_cohorts()
    expected = {
        17: {"due_2033": 1569, "peak": 539, "late": 686},
        14: {"due_2033": 1593, "peak": 1056, "late": 871},
        12: {"due_2033": 1616, "peak": 1086, "late": 901},
    }
    for life_cap, values in expected.items():
        scenario = build_cta_age_scenario(cohorts, life_cap)
        assert scenario["age_due_by_2033_slots"] == values["due_2033"]
        assert scenario["minimum_age_only_peak_annual_renewals"] == values["peak"]
        assert scenario["minimum_slots_missing_hard_deadline"] == values["late"]
        assert scenario["first_deadline_shortfall_year"] == 2024
        assert scenario["deadline_breaches_are_irrecoverable"] is True


def test_cta_age_fields_are_available_in_result_json():
    result = json.loads((ROOT / "results/three_city_roadmap.json").read_text())
    model = result["chicago"]["age_constrained_replacement_model"]
    assert model["annual_purchase_capacity"] == 185
    assert model["2024_shortfall_by_life_cap"]["17"] == 354
    assert model["2024_shortfall_by_life_cap"]["14"] == 871
    assert model["all_selected_life_caps_feasible_at_185"] is False
    assert "annual_plan" in result and "vancouver" in result and "london" in result
