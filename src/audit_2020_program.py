"""Reconcile TransLink's published December 2020 fleet-program update.

The award table and nominal cost table are a historical plan. Award year is
not delivery year, and its 2020--2030 boundary is not the HiMCM 2024--2033
scenario. This audit is a calibration benchmark only.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "https://www.translink.ca/-/media/translink/media-releases/2021/january/"
    "translink_low_carbon_fleet_transition_plan_update_2021_01_18.pdf"
)


def calculate() -> dict:
    path = ROOT / "data/processed/translink_2020_update_annual.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [int(row["year"]) for row in rows] == list(range(2020, 2031))
    for row in rows:
        row["year"] = int(row["year"])
        for key in ("standard_depot_awards", "standard_inroute_awards",
                    "articulated_depot_awards"):
            row[key] = int(row[key])
        row["incremental_vehicle_capital_nominal_mcad"] = (
            None if not row["incremental_vehicle_capital_nominal_mcad"]
            else float(row["incremental_vehicle_capital_nominal_mcad"])
        )
        row["incremental_operating_nominal_mcad"] = float(
            row["incremental_operating_nominal_mcad"]
        )
        row["planned_beb_awards"] = sum(
            row[key] for key in ("standard_depot_awards",
                                "standard_inroute_awards", "articulated_depot_awards")
        )
    award_counts = {
        key: sum(row[key] for row in rows)
        for key in ("standard_depot_awards", "standard_inroute_awards",
                    "articulated_depot_awards", "planned_beb_awards")
    }
    assert award_counts == {
        "standard_depot_awards": 449,
        "standard_inroute_awards": 136,
        "articulated_depot_awards": 92,
        "planned_beb_awards": 677,
    }
    vehicle_capital = round(sum(
        row["incremental_vehicle_capital_nominal_mcad"] or 0 for row in rows
    ), 1)
    operating_digitized = round(sum(
        row["incremental_operating_nominal_mcad"] for row in rows
    ), 1)
    assert vehicle_capital == 236.9
    assert operating_digitized == -96.1
    published_operating_total = -96.3  # Printed Table 5 total.
    infrastructure_total = 246.4       # Table 3, no annual spending schedule.
    nominal_incremental_total = round(
        vehicle_capital + infrastructure_total + published_operating_total, 1
    )
    assert nominal_incremental_total == 387.0
    return {
        "status": "RECONCILED_HISTORICAL_2020_PLAN_NOT_2023_OBSERVED",
        "source": SOURCE,
        "source_tables": {"awards_and_vehicle_capital": "Table 1, PDF p. 2",
                          "infrastructure": "Table 3, PDF p. 3",
                          "operating": "Table 5, PDF pp. 4--5"},
        "award_years_not_delivery_years": True,
        "planned_awards": award_counts,
        "annual": rows,
        "nominal_incremental_cost_mcad": {
            "vehicle_purchase_premium": vehicle_capital,
            "depot_and_charging": infrastructure_total,
            "published_operating_change": published_operating_total,
            "reconstructed_net_from_published_component_totals": nominal_incremental_total,
        },
        "rounding_audit": {
            "digitized_annual_operating_sum_mcad": operating_digitized,
            "source_published_operating_total_mcad": published_operating_total,
            "difference_mcad": round(operating_digitized - published_operating_total, 1),
            "explanation": "Annual Table 5 cells are printed to CAD 0.1m; their sum differs from the printed total by CAD 0.2m, consistent with rounding or underlying source precision. The printed total is retained for the overall nominal calculation.",
        },
        "exclusions": [
            "2020 award of 15 buses was funded under an earlier capital program and has no incremental cost in Table 1",
            "no facility spending years, so no justified discounted NPV",
            "not an actual 2023 fleet, a 2024--2033 plan, or proof of all-electric winter feasibility",
            "not a complete ordinary-renewal or full-fleet cost score",
        ],
    }


if __name__ == "__main__":
    result = calculate()
    target = ROOT / "results/2020_program_audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
