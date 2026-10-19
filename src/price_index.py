"""CPI rebasing for public price envelopes."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def factors() -> dict[int, float]:
    with (ROOT / "data/processed/canada_cpi_annual_2021_2025.csv").open(
            newline="", encoding="utf-8") as handle:
        return {int(row["year"]): float(row["factor_to_2023_cad"])
                for row in csv.DictReader(handle)}


def to_2023(value: float, source_year: int) -> float:
    f = factors()
    if source_year not in f:
        raise KeyError(f"CPI table has no source year {source_year}")
    return value * f[source_year]
