"""CPI rebasing for public price envelopes."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def factors() -> dict[int, float]:
    with (ROOT / "data/processed/canada_cpi_annual_2019_2025.csv").open(
            newline="", encoding="utf-8") as handle:
        return {int(row["year"]): float(row["factor_to_2023_cad"])
                for row in csv.DictReader(handle)}


def to_2023(value: float, source_year: int) -> float:
    f = factors()
    if source_year not in f:
        raise KeyError(f"CPI table has no source year {source_year}")
    return value * f[source_year]


def price_record(amount: float, source_year: int, *, currency: str = "CAD",
                 cad_per_unit: float = 1.0, source_scope: str,
                 source_id: str, fx_basis: str = "CAD; no FX",
                 status: str = "PUBLIC_ENVELOPE") -> dict:
    """Convert one source-year leaf once; aggregate only value_2023_cad."""
    if currency not in ("CAD", "USD") or cad_per_unit <= 0:
        raise ValueError("explicit currency and positive FX required")
    if currency == "CAD" and cad_per_unit != 1:
        raise ValueError("CAD leaf cannot receive FX conversion")
    return dict(amount=amount, source_year=source_year, currency=currency,
                cad_per_unit=cad_per_unit, FX_basis=fx_basis, base_year=2023,
                source_scope=source_scope, source_id=source_id, status=status,
                cpi_factor=factors()[source_year],
                value_2023_cad=to_2023(amount * cad_per_unit, source_year))
