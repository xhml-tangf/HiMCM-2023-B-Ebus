"""Rebuild the checked analyses from the local raw/processed source bundle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    "src/audit_data.py",
    "src/audit_service_actual.py",
    "src/audit_capacity_proxy.py",
    "src/audit_gtfs_baseline.py",
    "src/analyze_vancouver_blocks.py",
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
    "src/plot_transition_scenarios.py",
    "src/make_block_table.py",
    "src/make_depot_table.py",
    "src/make_three_city_roadmap.py",
    "src/run_analysis.py",
]


def main() -> None:
    for step in STEPS:
        print(f"RUN {step}", flush=True)
        subprocess.run([sys.executable, step], cwd=ROOT, check=True)
    print("RUN pytest", flush=True)
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
