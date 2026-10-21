"""Rebuild the checked analyses from the local raw/processed source bundle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    "src/audit_data.py",
    "src/audit_cpi.py",
    "src/price_catalog.py",
    "src/audit_service_actual.py",
    "src/audit_capacity_proxy.py",
    "src/audit_gtfs_baseline.py",
    "research/audit_vancouver_official_evidence_v3.py",
    "src/analyze_vancouver_blocks.py",
    "src/build_full_city_schedule_v3.py",
    "src/audit_deck_shuttle_electrification.py",
    "src/audit_apta_2023.py",
    "src/audit_fleet_snapshot.py",
    "src/audit_comparators.py",
    "src/audit_cta_2023.py",
    "src/optimize_london_cohorts.py",
    "src/plot_london_cohorts.py",
    "src/audit_2020_program.py",
    "src/audit_non_electric_lockin.py",
    "src/audit_service_floor.py",
    "src/plot_service_floor.py",
    "src/compute_reference_scores.py",
    "src/audit_capital_cohorts.py",
    "src/analyze_charging_tariffs.py",
    "src/plot_charging_tariffs.py",
    "src/build_transition_scenarios.py",
    "src/audit_regional_and_air_quality.py",
    "src/plot_transition_scenarios.py",
    "src/build_full_fleet_bound.py",
    "src/build_full_tco_bridge.py",
    "src/build_environment_bridge.py",
    "src/build_asset_boundary.py",
    "src/propagate_transition_uncertainty.py",
    "src/make_review_tables.py",
    "src/make_block_table.py",
    "src/make_depot_table.py",
    "src/make_three_city_roadmap.py",
    "src/build_threecity_execution_v3.py",
    "src/run_analysis.py",
    "scripts/run_research_model.py",
    "src/build_canonical_results.py",
    "scripts/build_paper_tables.py",
    "scripts/verify_research_model.py",
    "scripts/check_manuscript_numbers.py",
]


def main() -> None:
    for step in STEPS:
        print(f"RUN {step}", flush=True)
        subprocess.run([sys.executable, step], cwd=ROOT, check=True)
    print("RUN pytest", flush=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
