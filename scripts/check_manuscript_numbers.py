"""Guard key manuscript results against stale generated JSON values."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    text = (ROOT / "paper/ebus_transition.tex").read_text(encoding="utf-8")
    generic = json.loads((ROOT / "results/vancouver_transition_scenarios.json").read_text())
    central_generic = next(x for x in generic["economics"] if x["case"] == "central")
    high_generic = next(x for x in generic["economics"] if x["case"] == "high")
    env_min = min(x["environment_score_boundary_pct"] for x in generic["environment"])
    env_max = max(x["environment_score_boundary_pct"] for x in generic["environment"])
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    central_full = full["central_result"]
    asset = json.loads((ROOT / "results/vancouver_asset_boundary.json").read_text())
    asset_scores = [x["economic_score_pct"] for x in asset["combined_asset_and_infrastructure_cases"]]
    env_full_min = min(x["environment_score_pct"] for x in full["environment_central"])
    env_full_max = max(x["environment_score_pct"] for x in full["environment_central"])
    blocks = json.loads((ROOT / "results/vancouver_block_range_audit.json").read_text())
    weekday = next(x for x in blocks["days"] if x["kind"] == "weekday")
    req = next(x for x in weekday["range_scenarios"]
               if x["scenario"] == "40ft" and x["range_km"] == 300)
    req60 = next(x for x in weekday["range_scenarios"]
                 if x["scenario"] == "60ft" and x["range_km"] == 300)
    lower = req["fleet_blocks_after_ceiling_lower_distance"] + req60["fleet_blocks_after_ceiling_lower_distance"]
    upper = req["fleet_blocks_after_ceiling_upper_distance"] + req60["fleet_blocks_after_ceiling_upper_distance"]
    cta = json.loads((ROOT / "results/three_city_roadmap.json").read_text())
    execution = json.loads((ROOT / "results/threecity_execution_certificates_v3.json").read_text())
    fullcity = json.loads((ROOT / "results/vancouver_full_city_schedule_v3.json").read_text())
    tco = json.loads((ROOT / "results/vancouver_full_tco_bridge.json").read_text())
    environment = json.loads((ROOT / "results/vancouver_environment_bridge.json").read_text())
    cta_shortfalls = cta["chicago"]["age_constrained_replacement_model"]["2024_shortfall_by_life_cap"]
    expected = [
        f"{central_generic['plan_gross_pv_cad'] / 1e9:.2f}",
        f"{central_generic['baseline_gross_pv_cad'] / 1e9:.2f}",
        f"{central_generic['economic_score_gross_pct']:.1f}",
        f"{high_generic['economic_score_gross_pct']:.1f}",
        f"{env_min:.1f}",
        f"{env_max:.1f}",
        "1,406",
        "1,401",
        "1,647",
        "1,909",
        "1,927",
        f"{central_full['plan_gross_pv_cad'] / 1e9:.2f}",
        f"{central_full['baseline_gross_pv_cad'] / 1e9:.2f}",
        f"{central_full['economic_score_gross_pct']:.1f}",
        f"{-env_full_min:.1f}",
        f"{env_full_max:.1f}",
        f"{lower:,}--{upper:,}",
        "22,494",
        str(execution["chicago"]["2033_electrification_shortfall_under_fmp"]["total_purchase_shortfall"]),
        str(execution["chicago"]["2024_ramp_certificate"]["shortfall_after_430_vs_200_budgeted_deliveries"]),
        f"{fullcity['screened_pattern_trip_instances']:,}",
        str(max(x["group_peak_lower_bounds"]["heavy_non_deck"] for x in fullcity["patterns"])),
        f"{fullcity['worst_case']['uniform_turn_failures']['value']:,}",
        f"{min(x['economic_score_pct'] for x in tco['cases']):.1f}",
        f"{max(x['economic_score_pct'] for x in tco['cases']):.1f}",
        f"{min(x['environment_score_pct'] for x in environment['cases']):.1f}",
        f"{max(x['environment_score_pct'] for x in environment['cases']):.1f}",
        f"{min(asset_scores):.1f}",
        f"{max(asset_scores):.1f}",
        "constant 2023 CAD",
    ]
    missing = [value for value in expected if value not in text]
    stale = [
        value for value in (
            "4.709", "5.259", "-91.6", "35.1--84.0",
            "1,652", "1,932", "-81.7", "-104.1",
            "29.2--82.4", "35.3--84.0", "4.575", "-96.4",
            "price-mixed", "18 delivered", "-41.1", "-106.4",
            "$-41$ to $-106", "$-104$ to $-106",
            "-89.2", "-250.8", "-49.5", "-9.8", "-80.3",
            "-76.5", "-21.0", "-69.9", "-72.3", "-68.1", "3.1",
            "1,612", "1,419", "18 existing BEBs",
        ) if value in text
    ]
    if missing or stale:
        raise SystemExit(f"Manuscript number check failed: missing={missing}, stale={stale}")
    print("MANUSCRIPT NUMBER CHECK PASS: generic, class-specific and endpoint values agree")


if __name__ == "__main__":
    main()
