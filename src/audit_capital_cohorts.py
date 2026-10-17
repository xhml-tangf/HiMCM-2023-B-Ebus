"""Reproduce partial retirement/cohort and project-budget checks from TransLink's 2025 plan.

The capital-program table is retrospective evidence of named projects, not a 2023
fleet register, a delivered-vehicle invoice, or a service-feasible purchase plan.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "https://www.translink.ca/-/media/translink/documents/about-translink/"
    "corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf"
)
DEPOT_SOURCE = (
    "https://www.translink.ca/-/media/translink/documents/about-translink/"
    "policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf"
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

    articulated_2026 = next(
        row for row in electric
        if row["useful_life_year"] == 2026
        and row["planned_replacement_class"] == "articulated_60ft"
    )
    standard_2023 = next(
        row for row in electric
        if row["useful_life_year"] == 2023
        and row["planned_replacement_count"] == 57
    )
    budget = standard_2023["project_gross_budget_2025_report_mcad"]
    grant_cases = [
        {
            "hypothetical_grant_share_pct": int(100 * fraction),
            "gross_project_budget_mcad": budget,
            "grant_transfer_mcad_if_entire_budget_eligible": budget * fraction,
            "agency_payment_mcad_if_entire_budget_eligible": budget * (1 - fraction),
        }
        for fraction in (0, 0.25, 0.5)
    ]
    with (ROOT / "data/processed/translink_2020_depot_ratios.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        depots = list(csv.DictReader(handle))
    assert len(depots) == 7
    # TransLink 2020 Appendix C Table C-2 uses 660-kWh articulated BEBs with
    # supplemental fuel heat. It says electric-only heat needs about 10% more
    # buses on cold winter days. This is a historical stress test, not a
    # current 2026 procurement requirement or a certified service solution.
    articulated_depot_stress = [
        {
            "depot": row["depot"],
            "diesel_heater_depot_replacement_ratio_2020": float(row["articulated_60ft"]),
            "illustrative_electric_heat_ratio": 1.10 * float(row["articulated_60ft"]),
            "illustrative_electric_heat_buses_for_39_retirements": math.ceil(
                articulated_2026["retired_count"] * 1.10 * float(row["articulated_60ft"])
            ),
        }
        for row in depots
    ]
    for item in articulated_depot_stress:
        item["difference_from_2025_plan_45_bebs"] = (
            item["illustrative_electric_heat_buses_for_39_retirements"]
            - articulated_2026["planned_replacement_count"]
        )

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
        "illustrative_57_beb_project_grant_cases": {
            "status": "HYPOTHETICAL_FUNDING_ARITHMETIC_NOT_INCREMENTAL_COST_SCORE",
            "assumption": "The entire CAD 106.846m gross program budget is grant-eligible; actual eligibility and timing are not verified.",
            "reported_external_funding_mcad": standard_2023["external_funding_2025_report_mcad"],
            "cases": grant_cases,
            "warning": "The source-reported external funding is a later budget item, not the problem's maximum-50% counterfactual; a normal-renewal comparator is still needed for an economic score.",
        },
        "illustrative_2026_articulated_depot_electric_heat_stress": {
            "source": DEPOT_SOURCE,
            "assumptions": "2020 Appendix C-2 depot ratios for 660-kWh BEBs with fuel heat, multiplied by the source's approximate 1.10 electric-only-winter-heat fleet factor; all 39 retirement buses hypothetically allocated to one depot",
            "planned_2025_budget_bebs": articulated_2026["planned_replacement_count"],
            "cases_by_depot": articulated_depot_stress,
            "warning": "Only an old-technology sensitivity. Depot allocation, 2026 bus specifications, charging and individual trip blocks are unknown; this does not prove a real shortage.",
        },
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
