import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_uncertainty_grid_reproduces_named_case_and_orders_quantiles():
    result = json.loads(
        (ROOT / "results/vancouver_transition_uncertainty.json").read_text()
    )
    assert result["cells"] == 432_768
    assert result["grid"]["fleet_2023_total"] == {
        "min": 1711, "max": 1733, "step": 1, "count": 23
    }
    assert result["grid"]["baseline_fuel_intensity_kg_co2e_km"] == [
        0.302, 0.96, 1.233, 1.58
    ]
    reproduction = result["named_case_grid_reproduction"]
    assert reproduction["cases_matched"] == 1
    assert reproduction["net_new_battery_positions"] == 1612
    assert abs(reproduction["gross_pv_difference_cad"]) < 1.0
    assert abs(reproduction["economic_score_difference_pct_points"]) < 1e-8
    assert abs(reproduction["environment_score_difference_pct_points"]) < 1e-8
    assert result["service_km_control"]["independent_of_fleet_scenario"] is True

    for key in ("gross_pv_cad", "economic_score_pct", "environment_score_pct"):
        values = result[key]
        assert values["minimum"] <= values["p05"] <= values["median"]
        assert values["median"] <= values["p95"] <= values["maximum"]


def test_uncertainty_output_is_not_labelled_as_a_confidence_interval():
    result = json.loads(
        (ROOT / "results/vancouver_transition_uncertainty.json").read_text()
    )
    assert "NOT_A_CONFIDENCE_INTERVAL" in result["status"]
    assert "not sampling confidence intervals" in result["quantile_weighting"]
