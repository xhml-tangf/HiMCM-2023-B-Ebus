import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full_fleet_bound_reconciles_and_covers_named_classes():
    result = json.loads(
        (ROOT / "results/vancouver_full_fleet_bound.json").read_text()
    )
    assert result["classes"] == {
        "heavy_non_deck": 1424,
        "double_deck": 57,
        "community_shuttle_midpoint": 189,
        "existing_beb": 18,
    }
    central = result["central_result"]
    assert central["heavy_purchases_after_existing_beb"] == 1406
    assert abs(
        central["economic_score_gross_pct"]
        - 100
        * (central["baseline_gross_pv_cad"] - central["plan_gross_pv_cad"])
        / central["baseline_gross_pv_cad"]
    ) < 1e-9
    assert [x["grant_fraction"] for x in central["grant_cases"]] == [0.0, 0.25, 0.5]
    assert central["grant_cases"][2]["agency_pv_cad"] < central["grant_cases"][0]["agency_pv_cad"]


def test_full_fleet_environment_boundary_is_ordered():
    result = json.loads(
        (ROOT / "results/vancouver_full_fleet_bound.json").read_text()
    )
    scores = [x["environment_score_pct"] for x in result["environment_central"]]
    assert scores == sorted(scores)
    assert 35.0 < scores[0] < 36.0
    assert 83.0 < scores[-1] < 85.0
