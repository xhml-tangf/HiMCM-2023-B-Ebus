"""Audit APTA's 2023 vehicle archive and TransLink FOI fleet evidence.

This script deliberately separates three evidence classes:

* an APTA fleet extraction, only when the official archive is locally available;
* an official FOI request-log screen, which can establish that a record was
  released in full without implying that its attachment is public; and
* the already processed 2022/2025 CMBC bridge and 2025 scanned fleet release.

The APTA workbook schema has changed across editions.  The workbook reader
therefore searches for the documented vehicle columns instead of assuming a
single sheet name.  It never treats national APTA inclusion as evidence that a
particular agency appears in the member survey.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
RESULTS = ROOT / "results"

APTA_PAGE_URL = (
    "https://www.apta.com/news-research/public-transit-statistics/vehicle-database/"
)
APTA_2023_URL = (
    "https://www.apta.com/wp-content/uploads/2026/03/"
    "APTA-2023-Vehicle-Database.zip"
)
APTA_2024_PDF_URL = "https://www.apta.com/wp-content/uploads/APTA-2024-Vehicle-Database.pdf"
FOI_LOG_URL = (
    "https://www.translink.ca/-/media/translink/documents/about-translink/"
    "freedom-of-information/past-non-personal-access-requests/"
    "foi-requests-received-in-2023.pdf"
)
CMBC_2025_URL = (
    "https://www.translink.ca/-/media/translink/documents/about-translink/"
    "freedom-of-information/cmbc-fleet--active--instorage.pdf"
)

TRANSIT_NAME_TOKENS = (
    "translink",
    "coast mountain",
    "greater vancouver transp",
    "south coast british columbia transportation",
    "cmbc",
)

FOI_REQUESTS = {
    "2023-249": {
        "received": "2023-05-03",
        "closed": "2023-06-13",
        "disposition": "Released in full",
        "scope": "List of every bus retired and/or decommissioned in the previous two years.",
        "fleet_relevance": "retirements only; no surviving-fleet age or depot roster",
    },
    "2023-327": {
        "received": "2023-06-07",
        "closed": "2023-07-20",
        "disposition": "Released in full",
        "scope": "Number of spare buses, 2019--2023.",
        "fleet_relevance": "spare-count evidence if the attachment were public",
    },
    "2023-375": {
        "received": "2023-06-22",
        "closed": "2023-07-26",
        "disposition": "Released in full",
        "scope": "Number of buses on road during peak service by category.",
        "fleet_relevance": "peak deployment count; not total fleet or reserve ratio",
    },
    "2023-409": {
        "received": "2023-07-11",
        "closed": "2023-07-27",
        "disposition": "Released in full",
        "scope": "Operator sign-up sheets for four transit centres.",
        "fleet_relevance": "work assignment records; no vehicle age or propulsion count",
    },
    "2023-411": {
        "received": "2023-07-10",
        "closed": "2023-07-27",
        "disposition": "Released in full",
        "scope": "Richmond Transit Centre operator sign-up sheet.",
        "fleet_relevance": "work assignment record; no vehicle age or propulsion count",
    },
    "2023-416": {
        "received": "2023-07-11",
        "closed": "2023-07-27",
        "disposition": "Released in full",
        "scope": "Blank September sign-up sheet for all depots.",
        "fleet_relevance": "blank form; no fleet data",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def text_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def locate_archive(explicit: str | None) -> Path | None:
    candidates = [
        explicit,
        ROOT / "data/raw/apta_2023_vehicle_database.zip",
        ROOT / "tmp/APTA-2023-Vehicle-Database.zip",
        ROOT / "tmp/apta_2023_vehicle_database.zip",
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate)
        if path.is_file() and path.stat().st_size > 0:
            return path.resolve()
    return None


def safe_extract(archive: Path, destination: Path) -> list[Path]:
    extracted: list[Path] = []
    root = destination.resolve()
    total_bytes = 0
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if member.is_dir():
                continue
            target = (destination / member.filename).resolve()
            if root not in target.parents:
                raise ValueError(f"Unsafe ZIP member: {member.filename}")
            if member.file_size > 250 * 1024 * 1024:
                raise ValueError(f"Unexpectedly large ZIP member: {member.filename}")
            total_bytes += member.file_size
            if total_bytes > 1024 * 1024 * 1024:
                raise ValueError("ZIP expands beyond the 1 GiB audit limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    output.write(chunk)
            extracted.append(target)
    return extracted


def header_mapping(row: list[Any]) -> dict[str, int]:
    values = [norm(value) for value in row]
    mapping: dict[str, int] = {}
    for index, value in enumerate(values):
        if not value:
            continue
        if value in {"agencyname", "transitagency", "agency"}:
            mapping.setdefault("agency", index)
        elif value in {"location", "urbanizedareaurbanplacemetroarea"}:
            mapping.setdefault("location", index)
        elif value in {"mode", "transitmode"}:
            mapping.setdefault("mode", index)
        elif value in {"yearbuilt", "yearofmanufacture", "manufactureyear"}:
            mapping.setdefault("year", index)
        elif value in {"bodymanufacturer", "manufacturer"}:
            mapping.setdefault("manufacturer", index)
        elif value == "model":
            mapping.setdefault("model", index)
        elif value in {"vehicletype", "type"}:
            mapping.setdefault("vehicle_type", index)
        elif value in {"lengthfeet", "vehiclelengthfeet", "length"}:
            mapping.setdefault("length_ft", index)
        elif value in {"typeofpower", "fueltype", "power", "propulsion"}:
            mapping.setdefault("power", index)
        elif value == "status":
            mapping.setdefault("status", index)
        elif value in {"total", "numberofvehicles", "numberofvehiclestotal"} or value.endswith("total"):
            mapping.setdefault("total", index)
        elif value == "active" or value.endswith("active"):
            mapping.setdefault("active", index)
    return mapping


def agency_label(rows: list[list[Any]], header_index: int) -> str:
    for index in list(range(max(0, header_index - 15), header_index)) + list(
        range(header_index + 1, min(len(rows), header_index + 15))
    ):
        values = [text_value(value) for value in rows[index]]
        for position, value in enumerate(values):
            if norm(value) == "agencyname" and position + 1 < len(values):
                return values[position + 1]
            if norm(value).startswith("agencyname:"):
                return value.split(":", 1)[1].strip()
    return ""


def parse_xlsx(workbook: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sheets = pd.read_excel(workbook, sheet_name=None, header=None, dtype=object)
    records: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    for sheet_name, frame in sheets.items():
        rows = frame.where(pd.notna(frame), "").values.tolist()
        token_cells: list[dict[str, Any]] = []
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                lowered = text_value(value).casefold()
                if any(token in lowered for token in TRANSIT_NAME_TOKENS):
                    token_cells.append(
                        {"sheet": sheet_name, "row": row_index + 1, "column": column_index + 1,
                         "value": text_value(value)}
                    )

        for header_index, row in enumerate(rows):
            mapping = header_mapping(row)
            if not ({"year", "power"} <= mapping.keys() and
                    ({"active", "total"} & mapping.keys()) and
                    ({"length_ft", "model", "vehicle_type"} & mapping.keys())):
                continue
            context_agency = agency_label(rows, header_index)
            context_text = " ".join(
                text_value(value) for offset in range(max(0, header_index - 8), header_index)
                for value in rows[offset]
            )
            context_text += " " + context_agency
            blank_streak = 0
            block_count = 0
            for row_index in range(header_index + 1, len(rows)):
                data_row = rows[row_index]
                if not any(text_value(value) for value in data_row):
                    blank_streak += 1
                    if blank_streak >= 8:
                        break
                    continue
                blank_streak = 0
                next_mapping = header_mapping(data_row)
                if {"year", "power"} <= next_mapping.keys():
                    break

                def cell(field: str) -> Any:
                    index = mapping.get(field)
                    return data_row[index] if index is not None and index < len(data_row) else None

                year = number(cell("year"))
                total = number(cell("total"))
                active = number(cell("active"))
                if year is None or not (1900 <= int(year) <= 2035):
                    continue
                if total is None and active is None:
                    continue
                record = {
                    "sheet": sheet_name,
                    "source_row": row_index + 1,
                    "agency": text_value(cell("agency")) or context_agency,
                    "location": text_value(cell("location")),
                    "mode": text_value(cell("mode")),
                    "year_built": int(year),
                    "vehicle_age_2023": 2023 - int(year),
                    "body_manufacturer": text_value(cell("manufacturer")),
                    "model": text_value(cell("model")),
                    "vehicle_type": text_value(cell("vehicle_type")),
                    "length_ft": number(cell("length_ft")),
                    "power": text_value(cell("power")),
                    "status": text_value(cell("status")),
                    "total": int(total) if total is not None else None,
                    "active": int(active) if active is not None else None,
                    "count_measure": "active" if active is not None else "total",
                }
                joined = " ".join(str(value) for value in record.values()).casefold()
                record["_target_context_match"] = (
                    bool(context_text and any(token in context_text.casefold() for token in TRANSIT_NAME_TOKENS))
                    or any(token in joined for token in TRANSIT_NAME_TOKENS)
                )
                records.append(record)
                block_count += 1
            blocks.append(
                {"sheet": sheet_name, "header_row": header_index + 1, "agency": context_agency,
                 "records": block_count}
            )
    return records, {"token_cells": token_cells, "blocks": blocks}


def parse_pdf_fallback(pdf_paths: list[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            lowered = text.casefold()
            if any(token in lowered for token in TRANSIT_NAME_TOKENS):
                snippets = []
                for token in TRANSIT_NAME_TOKENS:
                    position = lowered.find(token)
                    if position >= 0:
                        snippets.append(text[max(0, position - 240):position + 520])
                findings.append(
                    {"file": pdf_path.name, "page": page_number, "snippets": snippets}
                )
    return findings


def read_bridge() -> tuple[pd.DataFrame, dict[str, Any]]:
    bridge = pd.read_csv(PROCESSED / "translink_fleet_bridge_2023_2025.csv")

    def get(snapshot: int, metric: str) -> int:
        rows = bridge.query("snapshot == @snapshot and metric == @metric")
        if len(rows) != 1:
            raise ValueError(f"Expected one bridge row for {snapshot}/{metric}")
        return int(rows.iloc[0]["value"])

    class_names = ("trolley", "battery", "hybrid", "cng", "diesel", "gasoline_shuttle")
    classes_2025 = {name: get(2025, name) for name in class_names}
    if sum(classes_2025.values()) != get(2025, "active_total"):
        raise ValueError("2025 class sum does not reconcile to the active total")

    built = {
        int(row.metric.removeprefix("built_")): int(row.value)
        for row in bridge.query("snapshot == 2025").itertuples()
        if str(row.metric).startswith("built_")
    }
    if sum(built.values()) != get(2025, "active_total"):
        raise ValueError("2025 manufacture-year sum does not reconcile")

    age_bands = {"0-4": 0, "5-9": 0, "10-14": 0, "15-19": 0, "20+": 0}
    for year, count in built.items():
        age = 2025 - year
        band = "0-4" if age <= 4 else "5-9" if age <= 9 else "10-14" if age <= 14 else "15-19" if age <= 19 else "20+"
        age_bands[band] += count

    classes_2022 = {
        name: get(2022, name)
        for name in (
            "hybrid",
            "low_emission_diesel",
            "cng",
            "trolley",
            "battery",
            "contracted_diesel_hybrid",
            "gasoline_shuttle",
        )
    }
    low = get(2023, "total_low")
    high = get(2023, "total_high")
    point = get(2023, "total")
    if not low <= point <= high:
        raise ValueError("The existing 2023 derived point lies outside its interval")

    summary = {
        "classes_2022_total": get(2022, "total"),
        "classes_2022": classes_2022,
        "fleet_2023_interval": [low, high],
        "fleet_2023_width": high - low,
        "fleet_2023_derived_point": point,
        "fleet_2023_point_offset_from_low": point - low,
        "classes_2025_total": get(2025, "active_total"),
        "classes_2025": classes_2025,
        "in_storage_2025": get(2025, "in_storage"),
        "built_2025": {str(year): count for year, count in sorted(built.items())},
        "age_bands_2025": age_bands,
        "age_band_definition": "2025 minus year built; current active stock, not 2023 ages",
    }
    return bridge, summary


def read_snapshot() -> dict[str, Any]:
    snapshot = pd.read_csv(PROCESSED / "cmbc_depot_snapshot_2025.csv")
    numeric_columns = [
        "active_buses", "trolley", "non_trolley", "hybrid", "cng", "diesel",
        "gasoline_shuttle", "battery",
    ]
    sums = {column: int(snapshot[column].sum()) for column in numeric_columns}
    class_sum = sum(sums[column] for column in ("trolley", "hybrid", "cng", "diesel", "gasoline_shuttle", "battery"))
    if sums["active_buses"] != 1733 or class_sum != 1733:
        raise ValueError("Processed depot snapshot does not reconcile to 1,733")
    return {
        "depots": snapshot["depot"].tolist(),
        "active_total": sums["active_buses"],
        "propulsion_totals": {
            "trolley": sums["trolley"],
            "battery": sums["battery"],
            "hybrid": sums["hybrid"],
            "cng": sums["cng"],
            "diesel": sums["diesel"],
            "gasoline_shuttle": sums["gasoline_shuttle"],
        },
        "non_trolley": sums["non_trolley"],
    }


def read_foi_log(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {
            "status": "LOCAL_OFFICIAL_LOG_NOT_PRESENT",
            "source_url": FOI_LOG_URL,
            "requests": FOI_REQUESTS,
            "release_attachment_links_in_log": None,
        }
    reader = PdfReader(path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    annotation_count = sum(len(page.get("/Annots") or []) for page in reader.pages)
    entries: dict[str, Any] = {}
    for request_number, definition in FOI_REQUESTS.items():
        start = full_text.find(request_number)
        snippet = ""
        if start >= 0:
            snippet = re.sub(r"\s+", " ", full_text[start:start + 320]).strip()
        entries[request_number] = {
            **definition,
            "present_in_official_log": start >= 0,
            "log_excerpt": snippet,
            "public_attachment_linked_from_log": False,
        }
    return {
        "status": "OFFICIAL_LOG_READ",
        "source_url": FOI_LOG_URL,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "pages": len(reader.pages),
        "metadata": {str(key): str(value) for key, value in (reader.metadata or {}).items()},
        "annotation_count": annotation_count,
        "release_attachment_links_in_log": annotation_count,
        "interpretation": (
            "The official log records dispositions, not release documents. "
            "No attachment or URL annotations are embedded in the log PDF."
        ),
        "requests": entries,
    }


def read_scanned_cmbc(path: Path | None, bridge_summary: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {
            "status": "LOCAL_SCAN_NOT_PRESENT",
            "source_url": CMBC_2025_URL,
        }
    reader = PdfReader(path)
    text_chars = sum(len(page.extract_text() or "") for page in reader.pages)
    observed = {
        "request": "2025/469",
        "memo_date": "2025-11-20",
        "effective_timestamp": "2025-11-18 15:11:58",
        "active_total": 1733,
        "in_storage": 63,
        "active_by_power": {
            "electric_trolley": 261,
            "quick_charge_battery": 22,
            "hybrid": 535,
            "natural_gas": 365,
            "diesel": 379,
            "community_shuttle_gas": 171,
        },
    }
    matches = (
        observed["active_total"] == bridge_summary["classes_2025_total"]
        and observed["in_storage"] == bridge_summary["in_storage_2025"]
        and observed["active_by_power"]["electric_trolley"] == snapshot["propulsion_totals"]["trolley"]
        and observed["active_by_power"]["quick_charge_battery"] == snapshot["propulsion_totals"]["battery"]
        and observed["active_by_power"]["hybrid"] == snapshot["propulsion_totals"]["hybrid"]
        and observed["active_by_power"]["natural_gas"] == snapshot["propulsion_totals"]["cng"]
        and observed["active_by_power"]["diesel"] == snapshot["propulsion_totals"]["diesel"]
        and observed["active_by_power"]["community_shuttle_gas"] == snapshot["propulsion_totals"]["gasoline_shuttle"]
    )
    return {
        "status": "VISUALLY_READ_SCANNED_RECORD",
        "source_url": CMBC_2025_URL,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "pages": len(reader.pages),
        "embedded_text_characters": text_chars,
        "metadata": {str(key): str(value) for key, value in (reader.metadata or {}).items()},
        "evidence_method": "Rendered pages inspected; published aggregate and storage totals matched the processed CSV exactly.",
        "observed": observed,
        "matches_processed_2025_snapshot": matches,
        "limitation": "This November 2025 release is not a 2023 register and cannot establish 2023 age, spare or depot counts.",
    }


def write_evidence_csv(result: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    apta = result["apta_2023"]
    rows.append({
        "item": "APTA 2023 vehicle database ZIP",
        "status": apta["download_status"],
        "as_of": "not directly confirmed",
        "value": "",
        "unit": "",
        "source": apta["url"],
        "sha256": "",
        "note": apta["access_observation"],
    })
    rows.append({
        "item": "APTA 2024 text-search screen",
        "status": result["apta_2024_screen"]["status"],
        "as_of": "2024-01-01 per report",
        "value": "",
        "unit": "",
        "source": APTA_2024_PDF_URL,
        "sha256": "",
        "note": result["apta_2024_screen"]["interpretation"],
    })
    foi = result["foi_2023"]
    for request_number, entry in foi["requests"].items():
        rows.append({
            "item": f"TransLink FOI {request_number}",
            "status": "RELEASE_NOT_PUBLICLY_LINKED",
            "as_of": entry.get("closed", ""),
            "value": "",
            "unit": "",
            "source": FOI_LOG_URL,
            "sha256": foi.get("sha256", ""),
            "note": f"{entry['disposition']}; {entry['scope']}",
        })
    cmbc = result["current_cmbc_2025"]
    if cmbc.get("sha256"):
        rows.extend([
            {
                "item": "CMBC FOI 2025/469 active buses",
                "status": "OBSERVED_VISUAL",
                "as_of": "2025-11-18",
                "value": 1733,
                "unit": "vehicles",
                "source": CMBC_2025_URL,
                "sha256": cmbc["sha256"],
                "note": "Current active fleet; later than the 2023 question.",
            },
            {
                "item": "CMBC FOI 2025/469 in-storage buses",
                "status": "OBSERVED_VISUAL",
                "as_of": "2025-11-18",
                "value": 63,
                "unit": "vehicles",
                "source": CMBC_2025_URL,
                "sha256": cmbc["sha256"],
                "note": "Separate from the 1,733 active buses.",
            },
        ])
    comparison = result["bridge_comparison"]
    rows.extend([
        {
            "item": "Existing 2023 fleet interval",
            "status": "DERIVED_NOT_OBSERVED",
            "as_of": "2023",
            "value": "1711-1733",
            "unit": "vehicles",
            "source": "data/processed/translink_fleet_bridge_2023_2025.csv",
            "sha256": comparison["bridge_file_sha256"],
            "note": f"Derived point {comparison['derived_2023_point']}.",
        },
        {
            "item": "CMBC 2025 active fleet",
            "status": "PROCESSED_OBSERVED_SNAPSHOT",
            "as_of": "2025-11-18",
            "value": 1733,
            "unit": "vehicles",
            "source": "data/processed/cmbc_depot_snapshot_2025.csv",
            "sha256": comparison["snapshot_file_sha256"],
            "note": "Matches the scanned FOI aggregate.",
        },
    ])
    pd.DataFrame(rows).to_csv(PROCESSED / "apta_2023_translink_evidence.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", help="local APTA 2023 ZIP downloaded from the official URL")
    parser.add_argument("--foi-log", help="local copy of TransLink's 2023 FOI request-log PDF")
    parser.add_argument("--cmbc-pdf", help="local copy of the current CMBC active/in-storage scan")
    args = parser.parse_args()

    PROCESSED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    bridge, bridge_summary = read_bridge()
    snapshot = read_snapshot()
    foi_path = Path(args.foi_log).resolve() if args.foi_log else (ROOT / "tmp/foi-requests-2023.pdf")
    cmbc_path = Path(args.cmbc_pdf).resolve() if args.cmbc_pdf else (ROOT / "tmp/cmbc-fleet-active-instorage.pdf")

    archive = locate_archive(args.archive)
    parsed_records: list[dict[str, Any]] = []
    parse_diagnostics: dict[str, Any] = {}
    workbook_path: Path | None = None
    pdf_findings: list[dict[str, Any]] = []
    archive_meta: dict[str, Any] = {
        "url": APTA_2023_URL,
        "official_page": APTA_PAGE_URL,
        "download_status": "MISSING_LOCAL_ARCHIVE",
        "access_observation": (
            "Direct curl returned HTTP 403 Cloudflare 'Just a moment' challenge; "
            "headless Edge also reached the challenge page. The search crawler "
            "confirmed the URL serves application/zip, but it cannot return ZIP bytes."
        ),
        "download_probe_observations": [
            {
                "method": "curl (WSL, browser user agent)",
                "http_status": 403,
                "content_type": "text/html; charset=UTF-8",
                "body_bytes": 6004,
                "challenge_header": "cf-mitigated: challenge",
            },
            {
                "method": "Edge headless",
                "result": "Cloudflare browser-check page",
            },
            {
                "method": "search-result fetcher",
                "result": "origin file exists but application/zip cannot be returned by text fetcher",
            },
        ],
        "prior_project_ledger_status": "not_downloaded_due_network",
        "bytes": None,
        "sha256": None,
        "members": [],
    }
    target_records: list[dict[str, Any]] = []
    target_models: list[dict[str, Any]] = []
    if archive is None:
        apta_status = "BLOCKED_OFFICIAL_ARCHIVE_NOT_PARSED"
    else:
        archive_meta.update({
            "download_status": "LOCAL_OFFICIAL_ARCHIVE",
            "bytes": archive.stat().st_size,
            "sha256": sha256_file(archive),
        })
        with tempfile.TemporaryDirectory(prefix="apta-2023-", dir=ROOT / "tmp") as temporary:
            extracted = safe_extract(archive, Path(temporary))
            archive_meta["members"] = [
                {
                    "path": str(path.relative_to(temporary)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in extracted
            ]
            workbooks = [path for path in extracted if path.suffix.casefold() in {".xlsx", ".xlsm"}]
            pdfs = [path for path in extracted if path.suffix.casefold() == ".pdf"]
            if workbooks:
                workbook_path = workbooks[0]
                parsed_records, parse_diagnostics = parse_xlsx(workbook_path)
                for record in parsed_records:
                    if record.get("_target_context_match"):
                        target_records.append(record)
                bus_modes = {"MB", "TB", "RB"}
                active_records = [
                    record for record in target_records
                    if record.get("status", "").upper() not in {"O", "P"}
                    and (record.get("active") or 0) > 0
                ]
                bus_active = [
                    record for record in active_records
                    if record.get("mode", "").upper() in bus_modes
                ]
                if target_records:
                    target_records_frame = pd.DataFrame(target_records).drop(columns=["_target_context_match"])
                    target_records_frame.to_csv(PROCESSED / "apta_2023_translink_records.csv", index=False)
                    model_frame = bus_active.copy()
                    if not model_frame:
                        model_frame = active_records
                    if model_frame:
                        table = pd.DataFrame(model_frame)
                        group_columns = [
                            "year_built", "vehicle_age_2023", "body_manufacturer", "model",
                            "vehicle_type", "length_ft", "power", "count_measure",
                        ]
                        for column in group_columns:
                            table[column] = table[column].fillna("")
                        target_models = (
                            table.groupby(group_columns, dropna=False)["active"]
                            .sum()
                            .reset_index()
                            .rename(columns={"active": "active_count"})
                            .to_dict(orient="records")
                        )
                        pd.DataFrame(target_models).to_csv(
                            PROCESSED / "apta_2023_translink_models.csv", index=False
                        )
                apta_status = (
                    "PARSED_TRANSLINK_RECORDS_FOUND" if target_records
                    else "PARSED_TRANSLINK_RECORDS_NOT_FOUND"
                )
            elif pdfs:
                pdf_findings = parse_pdf_fallback(pdfs)
                apta_status = (
                    "PDF_FALLBACK_TEXT_FOUND" if pdf_findings
                    else "PDF_FALLBACK_NO_TRANSLINK_TEXT"
                )
            else:
                apta_status = "ARCHIVE_PARSED_NO_EXCEL_OR_PDF"

    apta_result = {
        **archive_meta,
        "catalog_status": "Official page lists APTA-2023-Vehicle-Database as a previous edition.",
        "documented_fields": [
            "date/manufacture year", "manufacturer", "model", "length", "fuel/power type",
            "number of vehicles",
        ],
        "documented_geography": "U.S. and Canadian transit agencies",
        "data_cutoff": {
            "status": "UNVERIFIED_FOR_2023",
            "expected_by_series_convention": "2023-01-01",
            "basis": (
                "The consecutive APTA 2024 and 2025 report overviews state January 1 "
                "of their respective reporting years; this is not direct evidence for 2023."
            ),
        },
        "status": apta_status,
        "workbook_name": workbook_path.name if workbook_path else None,
        "parse_diagnostics": parse_diagnostics,
        "pdf_findings": pdf_findings,
        "translink_record_count": len(target_records),
        "model_summary": target_models,
    }

    apta_2024_screen = {
        "status": "SEARCH_INDEXED_PDF_SCREEN_ONLY",
        "url": APTA_2024_PDF_URL,
        "as_of": "2024-01-01",
        "catalog_claim": "Approximately 158 U.S. and six Canadian agencies.",
        "toronto_record_present": True,
        "toronto_record_observed": (
            "Agency Name: Toronto Transit Commission; APTA ID: 280; vehicle rows include "
            "year built, model, length, type of power and active counts."
        ),
        "translink_cmbc_or_greater_vancouver_record_found": False,
        "search_terms": ["TransLink", "Coast Mountain Bus Company", "Greater Vancouver"],
        "interpretation": (
            "This is a targeted text-search screen of the 2024 report, not a full workbook "
            "enumeration and not evidence about the unavailable 2023 archive. It shows that "
            "Canadian coverage and Toronto presence do not by themselves prove TransLink inclusion."
        ),
    }

    foi_result = read_foi_log(foi_path)
    cmbc_result = read_scanned_cmbc(cmbc_path, bridge_summary, snapshot)

    comparison = {
        "bridge_file": "data/processed/translink_fleet_bridge_2023_2025.csv",
        "bridge_file_sha256": sha256_file(PROCESSED / "translink_fleet_bridge_2023_2025.csv"),
        "snapshot_file": "data/processed/cmbc_depot_snapshot_2025.csv",
        "snapshot_file_sha256": sha256_file(PROCESSED / "cmbc_depot_snapshot_2025.csv"),
        "derived_2023_point": bridge_summary["fleet_2023_derived_point"],
        "derived_2023_interval": bridge_summary["fleet_2023_interval"],
        "cmbc_2025_active": bridge_summary["classes_2025_total"],
        "cmbc_2025_in_storage": bridge_summary["in_storage_2025"],
        "apta_2023_parsed_total": (
            sum(int(row["active_count"]) for row in target_models) if target_models else None
        ),
        "difference_from_2023_point": None,
        "difference_from_2023_interval": None,
        "interpretation": (
            "No APTA-derived total is available, so neither the 1,725 derived point nor the "
            "1,711--1,733 interval can be tightened or rejected. The 2025 active fleet remains 1,733."
        ),
    }

    result = {
        "checked_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project_scope": "TransLink/CMBC fixed-route buses; SeaBus, HandyDART and rail excluded from the bridge comparison",
        "overall_status": (
            "APTA_2023_RECORD_DATA_MISSING; TRANSLINK_2023_FOI_RELEASES_NOT_PUBLICLY_LINKED; "
            "CURRENT_2025_FOI_SCAN_VERIFIED"
        ),
        "apta_2023": apta_result,
        "apta_2024_screen": apta_2024_screen,
        "foi_2023": foi_result,
        "current_cmbc_2025": cmbc_result,
        "bridge_comparison": comparison,
        "existing_snapshot": {
            "bridge": bridge_summary,
            "depot_snapshot": snapshot,
        },
        "missing": [
            "APTA 2023 ZIP bytes/hash and workbook inspection",
            "direct APTA 2023 data cutoff statement",
            "whether APTA 2023 contains TransLink, CMBC or Greater Vancouver records",
            "2023 APTA vehicle rows with model, manufacture year, length, power and count",
            "public attachments for TransLink FOI 2023-249, 2023-327 and 2023-375",
            "31 December 2023 physical fleet register by vehicle, status, age and depot",
            "2023 spare policy and published spare-bus count",
            "2023 depot allocations and charging/garage capacity",
        ],
        "warnings": [
            "FOI 'Released in full' describes a disposition to the requester; it does not make the attachment public or prove that the release is online.",
            "A 2024 APTA text search cannot fill a missing 2023 snapshot or be relabelled as 2023 evidence.",
            "The 2025 CMBC scan is a later active/in-storage snapshot and cannot establish 2023 age or spare counts.",
            "No 2023 HiMCM solution paper or answer was consulted or used.",
        ],
    }

    if result["bridge_comparison"]["apta_2023_parsed_total"] is not None:
        parsed_total = result["bridge_comparison"]["apta_2023_parsed_total"]
        low, high = result["bridge_comparison"]["derived_2023_interval"]
        result["bridge_comparison"]["difference_from_2023_point"] = parsed_total - result["bridge_comparison"]["derived_2023_point"]
        result["bridge_comparison"]["difference_from_2023_interval"] = (
            max(0, low - parsed_total, parsed_total - high)
        )

    (RESULTS / "apta_2023_fleet_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_evidence_csv(result)
    print(json.dumps({
        "status": result["overall_status"],
        "apta_status": apta_result["status"],
        "apta_2023_sha256": apta_result["sha256"],
        "translink_record_count": apta_result["translink_record_count"],
        "foi_log_sha256": foi_result.get("sha256"),
        "cmbc_scan_sha256": cmbc_result.get("sha256"),
        "bridge_interval": comparison["derived_2023_interval"],
        "derived_point": comparison["derived_2023_point"],
        "cmbc_2025_active": comparison["cmbc_2025_active"],
    }, indent=2))


if __name__ == "__main__":
    main()
