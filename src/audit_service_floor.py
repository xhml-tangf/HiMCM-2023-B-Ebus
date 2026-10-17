"""Screen TransLink's later service plan against the fixed-2023-service rule.

The 2025 Investment Plan's A9 bus-hours series is retrospective future-plan
evidence, not a 2023-known input. Its accounting boundary must be reconciled
before a strict like-for-like policy comparison.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "https://www.translink.ca/-/media/translink/documents/plans-and-projects/"
    "ten-year-investment-plan/public-consultation/2025-investment-plan.pdf"
)


def calculate() -> dict:
    with (ROOT / "data/processed/translink_2025_investment_bus_hours.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    series = {int(row["year"]): int(row["planned_bus_service_hours_thousands"]) * 1000
              for row in rows}
    assert sorted(series) == list(range(2025, 2035))
    assert sum(series.values()) == 50_049_000  # Printed A9 2025--2034 total.
    actual = json.loads((ROOT / "results/actual_service_audit.json").read_text(
        encoding="utf-8"
    ))["bus_totals"]["service_hours"]
    comparison = {
        year: {
            "later_plan_bus_hours": hours,
            "conditional_difference_from_2023_actual_hours": hours - actual,
            "conditional_change_from_2023_actual_pct": 100 * (hours / actual - 1),
            "would_meet_fixed_2023_hour_floor_if_boundaries_match": hours >= actual,
        }
        for year, hours in series.items()
    }
    return {
        "status": "CONDITIONAL_SCOPE_COMPARISON_NOT_SCHEDULE_FEASIBILITY",
        "source": SOURCE,
        "source_table": "A9, printed p. 63; bus conventional-transit service hours, thousands",
        "baseline_2023_actual_fixed_route_bus_hours": actual,
        "later_plan_2025_2034_bus_hours": series,
        "comparison": comparison,
        "2033_conditional_hour_gap": comparison[2033]["conditional_difference_from_2023_actual_hours"],
        "boundary_warning": "The 2025 plan's 'Bus' projection and the 2023 actual bus-only total appear comparable but are not proven identical in service accounting. The later plan is not the constant-2023-service comparator; no direct policy score follows from this comparison.",
    }


if __name__ == "__main__":
    result = calculate()
    target = ROOT / "results/service_floor_audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
