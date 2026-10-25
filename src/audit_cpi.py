"""Build an auditable 2019--2025 CPI rebasing table to 2023 CAD."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
URL = ("https://www.bankofcanada.ca/valet/observations/V41690973/json"
       "?start_date=2019-01-01&end_date=2025-12-31")


def main() -> None:
    cache = ROOT / "materials/sources/raw/canada_cpi_monthly_2019_2025.json"
    if cache.exists():
        raw = cache.read_bytes()
    else:
        response = requests.get(URL, timeout=20)
        response.raise_for_status()
        raw = response.content
    payload = json.loads(raw)
    observations = [row for row in payload["observations"] if row.get("V41690973", {}).get("v")]
    by_year = {year: [] for year in range(2019, 2026)}
    for row in observations:
        year = int(row["d"][:4])
        by_year[year].append(float(row["V41690973"]["v"]))
    if any(len(values) != 12 for values in by_year.values()):
        raise ValueError("expected twelve monthly CPI observations per year")
    annual = {year: sum(values) / 12 for year, values in by_year.items()}
    target = annual[2023]
    rows = [{"year": year, "annual_cpi_2002_100": annual[year],
             "factor_to_2023_cad": target / annual[year]} for year in sorted(annual)]
    cache.write_bytes(raw)
    with (ROOT / "data/processed/canada_cpi_annual_2019_2025.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "status": "OBSERVED_BANK_OF_CANADA_CPI_ANNUAL_AVERAGES",
        "source": URL,
        "series": "V41690973 Total CPI, 2002=100",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "monthly_observations": len(observations),
        "annual": rows,
        "usage": "Price envelopes dated 2019--2025 can be multiplied by factor_to_2023_cad; the 3% rate then acts as a real discount scenario.",
        "boundary": "CPI is an economy-wide deflator, not a bus or electrical-construction cost index.",
    }
    (ROOT / "results/canada_cpi_audit.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
