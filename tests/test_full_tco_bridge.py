import json
from math import isclose
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tco_bridge_adds_only_missing_lifecycle_components():
    bridge = json.loads((ROOT / "results/vancouver_full_tco_bridge.json").read_text())
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    central = full["central_result"]
    for case in bridge["cases"]:
        assert case["added_pv_cad"] > 0
        assert isclose(case["plan_full_tco_pv_cad"],
                       central["plan_gross_pv_cad"]+case["added_pv_cad"])
        assert case["economic_score_pct"] < 0
    assert bridge["cases"][0]["added_pv_cad"] < bridge["cases"][1]["added_pv_cad"]
    assert set(bridge["already_in_central_ledger_not_added"]) >= {"bus maintenance and energy"}
