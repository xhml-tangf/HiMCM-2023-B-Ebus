"""Reproduce primary-source 2023 scale checks for the two transfer cities.

These are separate agency accounting boundaries, not matched electrification
scores or route/charger feasibility certificates.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def calculate() -> dict:
    # FTA 2023 Annual Agency Profile, CTA NTD ID 50066, pages 1--2.
    cta_available = 1_895
    cta_operated_max = 1_307
    cta_revenue_miles = 45_411_226
    cta = {
        "source": "https://www.transit.dot.gov/sites/fta.dot.gov/files/transit_agency_profile_doc/2023/50066.pdf",
        "source_period": "2023 annual, published later",
        "buses_available_for_maximum_service": cta_available,
        "buses_operated_in_maximum_service": cta_operated_max,
        "system_spare_count": cta_available - cta_operated_max,
        "system_spare_ratio_vs_operated_pct": 100 * (cta_available - cta_operated_max) / cta_operated_max,
        "average_bus_fleet_age_years": 11.2,
        "bus_revenue_miles": cta_revenue_miles,
        "bus_revenue_km": cta_revenue_miles * 1.609344,
        "bus_revenue_hours": 4_970_515,
        "bus_operating_expense_2023_usd": 971_019_017,
        "missing": ["2023 electric propulsion split", "vehicle blocks", "garage capacities"],
    }
    assert round(cta["system_spare_ratio_vs_operated_pct"], 1) == 45.0

    # TfL Bus Fleet Audit, 31 March 2023: contracted London bus fleet.
    london_total = 8_643
    london_electric = 950
    london_hydrogen = 20
    london_double = 6_198
    london_single = 2_445
    assert london_double + london_single == london_total
    london = {
        "source": "https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf",
        "source_period": "31 March 2023 stock, not calendar-year bus service",
        "contracted_bus_fleet": london_total,
        "electric_buses": london_electric,
        "hydrogen_buses_noneligible_for_strict_electric_endpoint": london_hydrogen,
        "non_electric_buses_at_audit": london_total - london_electric,
        "double_deck_buses": london_double,
        "single_deck_buses": london_single,
        "electric_share_pct": 100 * london_electric / london_total,
        "missing": ["2023 route blocks", "depot power", "eligible electric replacement specifications"],
    }
    return {
        "status": "OBSERVED_SCALE_ONLY",
        "warning": "CTA annual service/VAMS and TfL March fleet stock have different boundaries; neither gives a feasible 2033 electric schedule or score.",
        "chicago_cta": cta,
        "london_tfl": london,
    }


if __name__ == "__main__":
    result = calculate()
    dest = ROOT / "results/comparison_city_audit.json"
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
