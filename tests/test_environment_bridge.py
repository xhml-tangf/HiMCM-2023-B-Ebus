import json
from math import isclose
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_infrastructure_bridge_is_plan_only_and_horizon_consistent():
    bridge = json.loads((ROOT / "results/vancouver_environment_bridge.json").read_text())
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    assert len(bridge["cases"]) == 8
    low, high = bridge["infrastructure_t_range"]
    assert 0 < low < high
    by_base = {(x["fuel_case"], x["equipment_bound"]): x for x in bridge["cases"]}
    for original in full["environment_central"]:
        x = by_base[(original["case"], "low")]
        assert isclose(x["plan_t"], original["plan_boundary_t"]+low)
        assert x["environment_score_pct"] < 100
    assert bridge["depot_area"]["modeled_m2"] > bridge["depot_area"]["source_m2"]
