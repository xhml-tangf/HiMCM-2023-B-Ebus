"""Validate the public Vancouver evidence added in version 3."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "materials/sources/raw"
OUT = ROOT / "materials/research/data/processed"

SOURCES = {
    "translink_2020_fleet_plan": "translink_2020_fleet_plan.pdf",
    "translink_2021_fleet_update": "translink_2021_fleet_update.pdf",
    "translink_2023_june_tech": "translink_2023_june_technology_update.pdf",
    "translink_2023_june_board": "translink_2023_june_board.pdf",
    "translink_2024_zefpt": "translink_2024_playbook_summary.pdf",
}


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def pdf_text(path: Path) -> str:
    with fitz.open(path) as document:
        return compact("\n".join(page.get_text() for page in document))


def main() -> None:
    tabular = {}
    for name in ("vancouver_official_evidence_v3.csv",
                 "vancouver_vehicle_specs_v3.csv",
                 "vancouver_depot_capacity_2020.csv"):
        with (OUT / name).open(newline="", encoding="utf-8") as stream:
            tabular[name] = list(csv.DictReader(stream))
        if not tabular[name] or any(None in row for row in tabular[name]):
            raise ValueError(f"malformed or empty CSV: {name}")

    hashes = {name: hashlib.sha256((RAW / filename).read_bytes()).hexdigest()
              for name, filename in SOURCES.items()}
    texts = {name: pdf_text(RAW / filename) for name, filename in SOURCES.items()}

    assertions = {
        "all_depots_full": ("translink_2023_june_tech", "All our depots are full"),
        "june_beb_count": ("translink_2023_june_tech", "4 Battery-Electric Buses"),
        "june_trolley_count": ("translink_2023_june_tech", "262 Electric-Trolleys"),
        "capacity_need": ("translink_2023_june_tech", "+2,000 spaces"),
        "capacity_need_pct": ("translink_2023_june_tech", "nearly 90%"),
        "delivery_duration": ("translink_2023_june_tech", "6+ years"),
        "future_grid_load": ("translink_2024_zefpt", "78 MW"),
        "pre2035_centres": ("translink_2024_zefpt", "transit centres transitioning before 2035"),
        "new_feeds": ("translink_2024_zefpt", "Seven on-route charging locations"),
        "existing_depot_delivery": ("translink_2024_zefpt", "6-8 years"),
        "depot_capacity_312": ("translink_2020_fleet_plan", "312"),
        "depot_capacity_539": ("translink_2020_fleet_plan", "539"),
        "weight_envelope": ("translink_2020_fleet_plan", "19,550"),
        "charging_power": ("translink_2020_fleet_plan", "50 kW per bus"),
    }
    for key, (source, phrase) in assertions.items():
        if phrase not in texts[source]:
            raise AssertionError(f"{key}: phrase not found in {source}: {phrase}")

    depots = tabular["vancouver_depot_capacity_2020.csv"]
    capacities = sum(int(row["max_capacity_40ft_equivalent"]) for row in depots)
    operating_capacity = sum(int(row["max_capacity_40ft_equivalent"])
                             for row in depots if not row["depot"].startswith("Marpole"))
    direct = sum(int(row["assigned_total"]) for row in depots)
    if capacities != 2291 or operating_capacity != 1991 or direct != 1538:
        raise AssertionError((capacities, direct))

    with (ROOT / "data/processed/cmbc_depot_snapshot_2025.csv").open(
            newline="", encoding="utf-8") as stream:
        snapshot = list(csv.DictReader(stream))
    active_2025 = sum(int(row["active_buses"]) for row in snapshot)
    if active_2025 != 1733:
        raise AssertionError(active_2025)

    prior = json.loads((ROOT / "results/apta_2023_fleet_audit.json").read_text(encoding="utf-8"))
    result = {
        "status": "PARTIAL_PUBLIC_EVIDENCE; FULL_2023_OPERATIONAL_CERTIFICATE_STILL_UNAVAILABLE",
        "access_date": "2026-10-20",
        "verified": {
            "six_operating_centres_nominal_capacity_2020": operating_capacity,
            "total_including_planned_marpole": capacities,
            "direct_cmbc_assigned_buses_2020": direct,
            "contractor_assigned_buses_2020": 134,
            "total_cmbc_and_contractor_assigned_2020": direct + 134,
            "operating_transit_centres_2020": 6,
            "planned_marpole_capacity": 300,
            "june_2023_bebs": 4,
            "june_2023_trolleys": 262,
            "january_2023_bebs_before_expansion": 4,
            "lfse_plus_order": 15,
            "december_2023_electric_total_exact": 280,
            "december_2023_split_approximate": {"trolleys": 275, "bebs": 5},
            "all_depots_full_2023": True,
            "additional_spaces_needed_by_2035": 2000,
            "additional_space_requirement_percent": "nearly 90",
            "future_grid_load_mw_2040": 78,
            "existing_depot_power_delivery_years": [6, 8],
            "charger_ahead_of_delivery_months": [6, 12],
            "active_fleet_2025": active_2025,
            "active_storage_2025": 63,
        },
        "source_hashes": hashes,
        "external_source_records": {
            "translink_foi_2023_log": {
                "sha256": prior["foi_2023"]["sha256"],
                "bytes": prior["foi_2023"]["bytes"],
                "status": prior["foi_2023"]["status"],
            },
            "cmbc_active_instorage_2025": {
                "sha256": prior["current_cmbc_2025"]["sha256"],
                "bytes": prior["current_cmbc_2025"]["bytes"],
                "status": prior["current_cmbc_2025"]["status"],
            },
            "adl_enviro500ev_hk_2023": {
                "sha256": "5a2387976b003617f0fa6d5306a8a1da67c6b7e9273d8530def20683dc3e5e4d",
                "bytes": 866111,
                "status": "PUBLIC_MANUFACTURER_PDF",
            },
        },
        "source_assertions": {k: {"source": v[0], "phrase": v[1]}
                              for k, v in assertions.items()},
        "unresolved": [
            "31 December 2023 vehicle register by status, class, age, depot and propulsion",
            "2023 block-to-vehicle and block-to-garage mapping",
            "2023 depot occupancy and operational (not nominal) parking constraints",
            "site-specific firm power, transformer, feeder, interconnection cost and commissioning date",
            "candidate BEB axle-load and full-load payload certification on TransLink routes",
            "route-level winter kWh/km and accessory-heating profiles",
            "trolley feeder/rectifier concurrent firm capacity by segment",
            "authentic load and crowd counts for every assigned trip",
            "APTA 2023 TransLink/CMBC rows; official ZIP returned HTTP 403",
        ],
        "model_implication": {
            "initial_beb_scenario": "The 18-BEB subtraction is contradicted by the December approximate 275+5 split. Retain as stress only; use five BEB plus about 275 trolleys as the 2023 central inventory if no better register is obtained.",
            "depot_implication": "Nominal capacity alone does not prove feasibility: 2023 sources state all depots were full, while 2025 active fleet is below the 2020 nominal total. Mixed-class tracks, charging equipment and operational buffers are required.",
            "power_implication": "The 78 MW result is system-wide planning evidence, not site firm capacity. A 2033 accelerated case needs earlier site scheduling than the 2040 roadmap.",
        },
    }
    (OUT / "vancouver_official_evidence_v3.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["verified"], indent=2))


if __name__ == "__main__":
    main()
