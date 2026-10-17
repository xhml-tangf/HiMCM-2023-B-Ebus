"""Screen later procurement plans for non-electric vehicles before 2033.

This combines *distinct named projects* from 2025 and 2026 reports. It does
not combine the older 2026 articulated BEB project with the later 2026
236-diesel replacement project, because their cohort overlap is unresolved.
Nothing here is an in-service register or an accelerated-transition solution.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "2025_plan": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf",
    "2026_plan": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2026-business-plan-operating-and-capital-budget.pdf",
}


def calculate() -> dict:
    with (ROOT / "data/processed/translink_2025_plan_cohorts.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        old = list(csv.DictReader(handle))
    with (ROOT / "data/processed/translink_2026_plan_cohorts.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        later = list(csv.DictReader(handle))
    assert len(old) == 7 and len(later) == 2
    cng = [row for row in old if row["planned_replacement_propulsion"] == "cng"]
    cng_by_cohort = {
        int(row["useful_life_year"]): int(row["planned_replacement_count"])
        for row in cng
    }
    assert cng_by_cohort == {2023: 50, 2024: 84, 2025: 30}
    diesel_project = next(row for row in later if row["project_id"] == "2026_conventional_replacement")
    later_beb_project = next(row for row in later if row["project_id"] == "2028_conventional_replacement")
    diesel = int(diesel_project["planned_diesel_60ft"])
    route_beb = int(diesel_project["planned_standard_beb_inroute"])
    depot_beb = int(diesel_project["planned_standard_beb_depot"])
    retired = int(diesel_project["retired_count"])
    replacements = diesel + route_beb + depot_beb
    assert (diesel, route_beb, depot_beb, retired, replacements) == (39, 64, 153, 236, 256)
    assert int(later_beb_project["retired_count"]) == 27
    assert int(later_beb_project["planned_standard_beb_unspecified"]) == 31
    cng_total = sum(cng_by_cohort.values())
    # Pure vintage sensitivity: 2020 TransLink plan gives 17-year 40/60-ft
    # useful life and roughly CAD 1.0m per 60-ft diesel in 2019 currency.
    # Seven years of service means ten of seventeen remain at 2033 entry.
    unused_2019_mcad = diesel * 1.0 * (17 - (2033 - 2026)) / 17
    return {
        "status": "RETROSPECTIVE_NAMED_PROJECT_SCREEN_NOT_DELIVERIES",
        "sources": SOURCES,
        "2025_plan_named_cng_replacement_by_retirement_cohort": cng_by_cohort,
        "2025_plan_named_cng_replacements_total": cng_total,
        "2026_plan_236_diesel_replacement_project": {
            "retiring_diesel": retired,
            "planned_60ft_diesel": diesel,
            "planned_40ft_inroute_beb": route_beb,
            "planned_40ft_depot_beb": depot_beb,
            "planned_total_replacements": replacements,
            "planned_vehicle_count_ratio": replacements / retired,
            "gross_program_budget_mcad": float(diesel_project["gross_project_budget_mcad"]),
            "warning": "Project budget includes all 256 planned vehicles; it cannot price the 39 diesel buses separately.",
        },
        "2026_plan_2028_hybrid_replacement_project": {
            "retiring_hybrids": 27,
            "planned_40ft_bebs": 31,
            "planned_vehicle_count_ratio": 31 / 27,
            "gross_program_budget_mcad": float(later_beb_project["gross_project_budget_mcad"]),
        },
        "identified_non_electric_planned_replacements_across_2023_2026_retirement_cohorts": cng_total + diesel,
        "illustrative_39_diesel_early_retirement": {
            "status": "HISTORICAL_2019_CAD_STRAIGHT_LINE_PROXY_ONLY",
            "source_life_and_price": "https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf",
            "assumption": "All 39 planned 60-ft diesel buses enter service at start-2026 and leave at start-2033 after seven years; 17-year useful life; 2019-CAD unit price approximately 1.0m; no resale value included.",
            "remaining_useful_life_years_at_2033": 10,
            "unused_capital_proxy_2019_mcad_before_sale": unused_2019_mcad,
            "warning": "Book-style straight-line exposure is not the actual incremental resource cost or a delivered-bus price. Selling/redeploying buses and a true 2023-dollar price change the result.",
        },
        "interpretation": "The 203 named CNG/diesel vehicles in these plans would need to leave strict all-electric service by 2033 if procured and still operating; they are not verified deliveries and other non-electric programs may exist.",
        "double_count_warning": "The 2025 plan's 45 articulated BEBs for 39 retiring diesels is an earlier project description. The 2026 plan's 39 articulated diesels within a larger 236-bus project may overlap it. They are not added together.",
    }


if __name__ == "__main__":
    result = calculate()
    target = ROOT / "results/non_electric_lockin_audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
