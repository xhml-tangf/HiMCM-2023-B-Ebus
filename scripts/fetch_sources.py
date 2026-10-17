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
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "sources.json"

SOURCES = {
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
    "icct_2024_ebus_lca_method.pdf": "https://theicct.org/wp-content/uploads/2024/08/ID-118-%E2%80%93-E-bus-radar_final2.pdf",
    "cta_2022_charging_forward.pdf": "https://www.transitchicago.com/assets/1/6/Charging_Forward_Report_2-10-22_%28FINAL%29.pdf",
    "tfl_2023_bus_fleet_audit.pdf": "https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf",
}


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
