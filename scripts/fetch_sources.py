"""Fetch public primary sources and record byte-level provenance.

Network access is needed. Existing files are reused unless --refresh is given.
The script does not scrape 2023 HiMCM submissions or model solutions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "materials" / "sources" / "raw"
MANIFEST = ROOT / "materials" / "sources" / "sources.json"

SOURCES = {
    "bchydro_2023_24_financial_statements.pdf": "https://www2.gov.bc.ca/assets/gov/british-columbians-our-governments/government-finances/public-accounts/2023-24/sup-e/bc-hydro-fs-2023-24.pdf",
    "bchydro_2023_approved_tariff.pdf": "https://www.bchydro.com/content/dam/BCHydro/customer-portal/documents/corporate/suppliers/transmission-scheduling/bulletins/2023/2023_08_03_BCUC_EXEC_TRFF_PGS.pdf",
    "translink_2023_business_plan.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2023_business_plan_operating_and_capital_budget.pdf",
    "cmbc_fleet_2025_active_instorage.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/freedom-of-information/cmbc-fleet--active--instorage.pdf",
    "apta_2023_vehicle_database.zip": "https://www.apta.com/wp-content/uploads/2026/03/APTA-2023-Vehicle-Database.zip",
    "statistics_canada_2021_cma_population.html": "https://www150.statcan.gc.ca/n1/daily-quotidien/220209/t002a-eng.htm",
    "translink_tspr_2023_annual.csv": "https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/csv-data/2023/tspr2023_bus_yearline.csv",
    "translink_tspr_2023_hourly.csv": "https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/csv-data/2023/tspr2023_bus_yearlinedaytypeseasontimerange.csv",
    "translink_tspr_2023_peakload.csv": "https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/csv-data/2023/tspr2023_bus_peakload_yearlinedaytypeseasontimerangedirection.csv",
    "translink_2023_tspr.pdf": "https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/2023_transit_service_performance_review.pdf",
    "translink_2018_service_guidelines.pdf": "https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/transit-oriented-communities/transit-services-guidelines-public-summary.pdf",
    "translink_2023_statutory.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/statutory_annual_report/2023_statutory_annual_report.pdf",
    "translink_2023_accountability.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/accountability_reports/2023/accountability_report_2023.pdf",
    "translink_2020_fleet_plan.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf",
    "translink_2021_fleet_update.pdf": "https://www.translink.ca/-/media/translink/media-releases/2021/january/translink_low_carbon_fleet_transition_plan_update_2021_01_18.pdf",
    "translink_2023_june_board.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/board-of-directors/board-minutes-and-reports/2023/june/23-06-22-public-board-meeting-package---for-posting.pdf",
    "translink_2023_june_technology_update.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf",
    "translink_2024_playbook_summary.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf",
    "translink_2024_business_plan.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2024-business-plan-operating-and-capital-budget-summary.pdf",
    "translink_2025_business_plan.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf",
    "translink_2026_business_plan.pdf": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2026-business-plan-operating-and-capital-budget.pdf",
    "translink_2025_investment_plan.pdf": "https://www.translink.ca/-/media/translink/documents/plans-and-projects/ten-year-investment-plan/public-consultation/2025-investment-plan.pdf",
    "icct_2024_ebus_lca_method.pdf": "https://theicct.org/wp-content/uploads/2024/08/ID-118-%E2%80%93-E-bus-radar_final2.pdf",
    "cta_2022_charging_forward.pdf": "https://www.transitchicago.com/assets/1/6/Charging_Forward_Report_2-10-22_%28FINAL%29.pdf",
    "cta_2024_budget.pdf": "https://www.transitchicago.com/assets/1/6/FY24_Budget_Book_ADA_Accessible_Text.pdf",
    "cta_2023_age_distribution.json": "https://data.transportation.gov/resource/6abt-uhgq.json?%24where=ntd_id%3D%2750066%27%20AND%20report_year%3D%272023%27",
    "cta_2023_fuel_energy.json": "https://data.transportation.gov/resource/8ehq-7his.json?%24where=ntd_id%3D%2750066%27%20AND%20report_year%3D%272023%27",
    "tfl_2023_bus_fleet_audit.pdf": "https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf",
}

# Original TransLink 23SEP_20231020 GTFS retained by an independent public
# mirror. The immutable Git commit is intentional: never replace with master.
GTFS_2023_MIRROR = (
    "https://raw.githubusercontent.com/JaydenCWong/JAAM-project/"
    "eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b/backend/engine/translink_data/"
)
SOURCES.update({
    f"vancouver_gtfs_2023/{name}": GTFS_2023_MIRROR + name
    for name in ("agency.txt", "feed_info.txt", "calendar.txt", "calendar_dates.txt",
                 "routes.txt", "trips.txt", "stop_times.txt", "stops.txt", "shapes.txt",
                 "directions.txt", "direction_names_exceptions.txt", "pattern_id.txt",
                 "signup_periods.txt", "stop_order_exceptions.txt", "notes.txt")
})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    entries = []
    session = requests.Session()
    session.headers["User-Agent"] = "Academic research reproducibility check/1.0"
    for name, url in SOURCES.items():
        target = RAW / name
        target.parent.mkdir(parents=True, exist_ok=True)
        status = "cached"
        if not target.exists() or args.refresh:
            try:
                response = session.get(url, timeout=90)
                response.raise_for_status()
                data = response.content
                if name.endswith(".pdf") and not data.startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                if name.endswith(".csv") and b"," not in data[:200]:
                    raise ValueError("response is not a CSV")
                if name.endswith(".json"):
                    response.json()
                target.write_bytes(data)
                status = "downloaded"
            except Exception as exc:
                status = f"unavailable: {type(exc).__name__}: {exc}"
        if target.exists():
            data = target.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            size = len(data)
        else:
            digest = None
            size = None
        entries.append({"file": name, "url": url, "status": status,
                        "bytes": size, "sha256": digest})
        print(f"{name}: {status}, {size} bytes")
    MANIFEST.write_text(json.dumps({
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sources": entries,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
