"""Recover implied *average* vehicle capacities in the 2023 TSPR cells.

This is a diagnostic, not a vehicle roster or a trip-capacity certificate.
The 2018 TransLink Service Guidelines define peak load factor as average
peak passengers divided by vehicle practical capacity. A ratio from an
aggregated 2023 cell can match a class reference but cannot identify every
vehicle used on that route or its actual battery-bus replacement capacity.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/vancouver_route_time_load_2023.csv"
OUTPUT = ROOT / "data/processed/vancouver_load_capacity_proxy_2023.csv"
SUMMARY = ROOT / "results/capacity_proxy_audit.json"
GUIDELINES = (
    "https://www.translink.ca/-/media/translink/documents/plans-and-projects/"
    "managing-the-transit-network/transit-oriented-communities/"
    "transit-services-guidelines-public-summary.pdf"
)
CAPACITY_CLASS = {
    24: "mini_bus_reference",
    47: "standard_trolley_reference",
    50: "standard_bus_or_highway_coach_reference",
    70: "articulated_trolley_reference",
    75: "articulated_bus_reference",
    85: "double_deck_like_inferred_not_2018_table",
}
TOLERANCE_PASSENGERS = 0.0001


def calculate() -> dict:
    enriched = []
    counts = Counter()
    route_classes: dict[str, set[str]] = defaultdict(set)
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        passengers = float(row["average_peak_passengers"] or 0)
        load_pct = float(row["average_peak_load_factor_pct"] or 0)
        if passengers <= 0 or load_pct <= 0:
            continue
        proxy = 100 * passengers / load_pct
        nearest = min(CAPACITY_CLASS, key=lambda value: abs(proxy - value))
        matches = abs(proxy - nearest) <= TOLERANCE_PASSENGERS
        label = CAPACITY_CLASS[nearest] if matches else "unmatched_aggregate"
        enriched.append({**row, "implied_average_capacity": f"{proxy:.6f}",
                         "reference_capacity_match": nearest if matches else "",
                         "capacity_reference_label": label})
        counts[label] += 1
        route_classes[row["route"]].add(label)
    assert len(enriched) == 9371  # Published 2023 CSV nonmissing load cells.
    assert sum(counts.values()) == len(enriched)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(enriched[0]))
        writer.writeheader()
        writer.writerows(enriched)
    summary = {
        "status": "AGGREGATE_CLASS_DIAGNOSTIC_NOT_VEHICLE_ROSTER",
        "source": GUIDELINES,
        "source_pages": "printed pp. 21 and 49 (PDF pp. 22 and 50)",
        "input_2023_tspr_positive_cells": len(enriched),
        "routes_with_positive_cells": len(route_classes),
        "reference_capacity_matches": len(enriched) - counts["unmatched_aggregate"],
        "reference_capacity_match_pct": 100 * (1 - counts["unmatched_aggregate"] / len(enriched)),
        "cells_by_reference_class": dict(sorted(counts.items())),
        "unmatched_aggregate_cells": counts["unmatched_aggregate"],
        "routes_with_multiple_labels": sum(len(labels) > 1 for labels in route_classes.values()),
        "routes_with_85_proxy": sorted(
            route for route, labels in route_classes.items()
            if CAPACITY_CLASS[85] in labels
        ),
        "warning": (
            "2018 capacity references are averages and the 2023 TSPR cells "
            "aggregate trips. 85 is not in the 2018 table; it is only "
            "consistent with TransLink's 80-86-seat double-deck pilot. "
            "Unmatched ratios can reflect mixed vehicle types, actual layouts "
            "or differences in averaging. No individual trip or replacement "
            "vehicle capacity is identified."
        ),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(calculate(), indent=2))
