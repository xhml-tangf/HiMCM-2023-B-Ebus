"""Reproduce the official 2023 fixed-route bus service totals.

The 2025 TransLink Business Plan p. 23 reports 2023 actual hours, vehicle-km
and capacity-km by operating group. SeaBus is excluded from the bus boundary.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "https://www.translink.ca/-/media/translink/documents/about-translink/"
    "corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf"
)


def calculate() -> dict:
    path = ROOT / "data/processed/translink_2023_actual_service.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert len({row["service_group"] for row in rows}) == 5
    for row in rows:
        for field in ("service_hours", "service_km", "capacity_km"):
            row[field] = int(row[field])
            assert row[field] > 0
    def sum_field(records: list[dict], field: str) -> int:
        return sum(row[field] for row in records)

    all_groups = {
        field: sum_field(rows, field)
        for field in ("service_hours", "service_km", "capacity_km")
    }
    assert all_groups == {
        "service_hours": 5_589_485,
        "service_km": 107_053_694,
        "capacity_km": 5_787_158_724,
    }
    bus = [row for row in rows if row["fixed_route_bus"] == "yes"]
    bus_totals = {
        field: sum_field(bus, field)
        for field in ("service_hours", "service_km", "capacity_km")
    }
    assert bus_totals == {
        "service_hours": 5_575_772,
        "service_km": 106_868_324,
        "capacity_km": 5_715_791_401,
    }
    route_audit = json.loads(
        (ROOT / "data/processed/vancouver_data_audit.json").read_text(encoding="utf-8")
    )
    route_hours = route_audit["csv_annual_service_hours"]
    with (ROOT / "data/processed/vancouver_route_annual_2023.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        route_rows = list(csv.DictReader(handle))
    route_revenue_km_scale = round(sum(
        float(row["revenue_hours_2023"]) * float(row["average_speed_kmh_2023"])
        for row in route_rows
    ))
    return {
        "status": "OBSERVED_2023_ACTUAL_PUBLISHED_IN_2025",
        "source": SOURCE,
        "source_page": 23,
        "scope": "CMBC conventional and shuttle, West Vancouver bus, and contracted community shuttle; SeaBus excluded",
        "bus_totals": {
            **bus_totals,
            "average_capacity_km_per_service_km": (
                bus_totals["capacity_km"] / bus_totals["service_km"]
            ),
        },
        "groups": [
            {
                "service_group": row["service_group"],
                "service_hours": row["service_hours"],
                "service_km": row["service_km"],
                "capacity_km": row["capacity_km"],
                "reported_capacity_km_per_service_km": (
                    row["capacity_km"] / row["service_km"]
                ),
            }
            for row in bus
        ],
        "all_groups_including_seabus_for_source_reconciliation": all_groups,
        "route_file_hours": route_hours,
        "route_hours_share_of_exact_bus_hours": route_hours / bus_totals["service_hours"],
        "route_speed_times_revenue_hours_km_scale": route_revenue_km_scale,
        "route_km_scale_share_of_actual_bus_service_km": (
            route_revenue_km_scale / bus_totals["service_km"]
        ),
        "boundary_warning": "The route speed×revenue-hours value is an estimator, not total service km; its gap to actual km must not be attributed wholly to deadhead without block data.",
    }


if __name__ == "__main__":
    result = calculate()
    target = ROOT / "results/actual_service_audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
