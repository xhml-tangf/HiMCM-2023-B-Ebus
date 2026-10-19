import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full_fleet_bound_reconciles_and_covers_named_classes():
    result = json.loads(
        (ROOT / "results/vancouver_full_fleet_bound.json").read_text()
    )
    assert result["classes"] == {
        "heavy_non_deck": 1419,
        "double_deck": 57,
        "community_shuttle_midpoint": 189,
        "existing_beb": 18,
    }
    central = result["central_result"]
    assert central["heavy_purchases_after_existing_beb"] == 1401
    assert abs(central["shared_depot_cad"] - 1419 * 500_000_000 / 340) < 1e-6
    assert result["initial_stock_2023"]["total"] == 1725
    assert result["endpoint_2033"] == {
        "electric_stock": 1927,
        "conventional_stock": 0,
        "net_new_beb_purchases": 1647,
        "trolley_replacement_purchases": 262,
        "total_electric_vehicle_purchases": 1909,
        "additional_service_positions": 202,
    }
    inventory = result["central_annual_inventory"]
    assert len(inventory) == 10
    assert sum(x["total_beb_purchases"] for x in inventory) == 1647
    assert sum(x["trolley_replacement_purchases"] for x in inventory) == 262
    assert sum(x["total_electric_vehicle_purchases"] for x in inventory) == 1909
    assert sum(x["conventional_retirements"] for x in inventory) == 1445
    assert inventory[-1]["electric_stock_end"] == 1927
    assert inventory[-1]["conventional_stock_end"] == 0
    assert abs(
        central["economic_score_gross_pct"]
        - 100
        * (central["baseline_gross_pv_cad"] - central["plan_gross_pv_cad"])
        / central["baseline_gross_pv_cad"]
    ) < 1e-9
    assert [x["grant_fraction"] for x in central["grant_cases"]] == [0.0, 0.25, 0.5]
    assert central["grant_cases"][2]["agency_pv_cad"] < central["grant_cases"][0]["agency_pv_cad"]
    assert "Common trolley replacement is excluded" in central["grant_scope"]
    common_grants = central["grant_cases_symmetric_common_trolley"]
    assert common_grants[2]["baseline_agency_pv_cad"] < common_grants[0]["baseline_agency_pv_cad"]
    assert -20.0 < common_grants[2]["agency_economic_score_vs_baseline_pct"] < 20.0


def test_full_fleet_environment_boundary_is_ordered():
    result = json.loads(
        (ROOT / "results/vancouver_full_fleet_bound.json").read_text()
    )
    scores = [x["environment_score_pct"] for x in result["environment_central"]]
    assert scores == sorted(scores)
    assert scores[0] < 0 < scores[-1]
    assert "community-shuttle body and powertrain production" in result[
        "production_components_t_central"
    ]["omitted_or_proxy_components"]


def test_shuttle_body_boundary_is_symmetric_and_ramp_is_used():
    result = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    assert result["manufacturing_boundary"]["shuttle_body_both_paths"] == "OMITTED_UNKNOWN"
    for case in result["environment_central"]:
        assert abs(case["baseline_production_t"] - 705 * 11429 * 6.6 / 1000) < 1e-6
        km = result["service_km"]["full_scored_proxy"]
        g = case["baseline_operating_g_per_km"] / 1000
        assert abs(case["plan_operating_t"] - km * (7.4 * g + 2.6 * .019) / 1000) < 1e-6


def test_route_purchases_follow_facility_readiness():
    result = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    purchases = [x["total_beb_purchases"] for x in result["central_annual_inventory"]]
    assert sum(purchases[:5]) == 0
    assert sum(purchases[5:]) == 1647
    assert result["central_annual_inventory"][-1]["conventional_stock_end"] == 0


def test_annual_class_ledger_conserves_service_km_and_tracks_energy():
    result = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    total_km = result["service_km"]["full_scored_proxy"]
    for row in result["annual_class_ledger"]:
        assert abs(sum(x["annual_scored_km"] for x in row["classes"].values()) - total_km) < 1e-6
        for cls in row["classes"].values():
            assert abs(cls["conventional_km"] + cls["electric_km"] - cls["annual_scored_km"]) < 1e-6
            assert cls["electric_grid_mwh_at_90pct_efficiency"] >= 0
