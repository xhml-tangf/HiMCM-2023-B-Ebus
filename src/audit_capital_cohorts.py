"""Reproduce partial retirement/cohort and project-budget checks from TransLink's 2025 plan.

The capital-program table is retrospective evidence of named projects, not a 2023
fleet register, a delivered-vehicle invoice, or a service-feasible purchase plan.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "https://www.translink.ca/-/media/translink/documents/about-translink/"
    "corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf"
)


def calculate() -> dict:
    path = ROOT / "data/processed/translink_2025_plan_cohorts.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 7
    for row in rows:
        row["useful_life_year"] = int(row["useful_life_year"])
        row["retired_count"] = int(row["retired_count"])
        row["planned_replacement_count"] = int(row["planned_replacement_count"])
        row["project_gross_budget_2025_report_mcad"] = float(
            row["project_gross_budget_2025_report_mcad"]
        )
        row["external_funding_2025_report_mcad"] = float(
            row["external_funding_2025_report_mcad"]
        )
        assert row["retired_count"] > 0 and row["planned_replacement_count"] > 0
        assert row["status"] == "planned_project_not_deliveries"

    electric = [
        row for row in rows
        if row["planned_replacement_propulsion"] == "battery_electric"
    ]
    electric_by_class: dict[str, dict] = {}
    for vehicle_class in sorted({row["planned_replacement_class"] for row in electric}):
        group = [row for row in electric if row["planned_replacement_class"] == vehicle_class]
        electric_by_class[vehicle_class] = {
            "retiring_vehicles_in_identified_projects": sum(row["retired_count"] for row in group),
            "planned_bebs_in_identified_projects": sum(row["planned_replacement_count"] for row in group),
            "project_gross_budget_mcad": sum(row["project_gross_budget_2025_report_mcad"] for row in group),
            "project_external_funding_mcad": sum(row["external_funding_2025_report_mcad"] for row in group),
            "project_gross_budget_mcad_per_planned_beb": (
                sum(row["project_gross_budget_2025_report_mcad"] for row in group)
                / sum(row["planned_replacement_count"] for row in group)
            ),
            "project_planned_replacement_ratio": (
                sum(row["planned_replacement_count"] for row in group)
                / sum(row["retired_count"] for row in group)
            ),
        }

    by_year = defaultdict(lambda: {"identified_retirements": 0, "planned_replacements": 0})
    for row in rows:
        item = by_year[row["useful_life_year"]]
        item["identified_retirements"] += row["retired_count"]
        item["planned_replacements"] += row["planned_replacement_count"]

    return {
        "status": "RETROSPECTIVE_PARTIAL_CAPITAL_COHORT_AUDIT",
        "source": SOURCE,
        "source_table_pages": [50, 51],
        "price_basis": "gross program budgets as printed in the 2025 Business Plan; CAD million",
        "all_identified_projects_by_useful_life_year": dict(sorted(by_year.items())),
        "beb_replacement_projects_by_class": electric_by_class,
        "individual_beb_projects": [
            {
                "useful_life_year": row["useful_life_year"],
                "retired_count": row["retired_count"],
                "planned_beb_count": row["planned_replacement_count"],
                "planned_replacement_ratio": row["planned_replacement_count"] / row["retired_count"],
                "project_gross_budget_mcad_per_planned_beb": row["project_gross_budget_2025_report_mcad"] / row["planned_replacement_count"],
            }
            for row in electric
        ],
        "limits": [
            "Named projects are not a complete fixed-route fleet age or depot register.",
            "A useful-life year is not proof that buses were retired or replacements delivered that year.",
            "A project budget divided by bus count is not a bus hardware bid or delivered unit price.",
            "Replacement ratios in capital plans do not certify matched service capacity or exact trip feasibility.",
            "The 2025 plan is retrospective evidence and must not be treated as information known at the 2023 decision date.",
        ],
    }


if __name__ == "__main__":
    result = calculate()
    target = ROOT / "results/capital_cohort_audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
