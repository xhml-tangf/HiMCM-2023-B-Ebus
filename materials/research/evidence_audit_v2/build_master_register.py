"""Merge current evidence assets with valid historical-only recovered facts."""
from __future__ import annotations

import difflib
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data_asset_inventory.csv"
HISTORY = HERE / "historical_recovery.csv"
SOURCES = HERE / "source_index.csv"
OUTPUT = HERE / "evidence_master_register.csv"


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def similarity(a: str, b: str) -> float:
    aa, bb = norm(a), norm(b)
    ta, tb = set(aa.split()), set(bb.split())
    jaccard = len(ta & tb) / max(1, len(ta | tb))
    return max(jaccard, difflib.SequenceMatcher(None, aa, bb).ratio())


def normalize_url(value: str) -> str:
    return str(value).strip().rstrip("/").lower().replace("http://", "https://")


def main() -> None:
    data = pd.read_csv(DATA, dtype=str).fillna("")
    hist = pd.read_csv(HISTORY, dtype=str).fillna("")
    sources = pd.read_csv(SOURCES, dtype=str).fillna("")
    url_to_source = {normalize_url(r.url): r.source_id for _, r in sources.iterrows() if r.url}

    # Cross-reference every historical record to the closest current fact, but
    # only append historical-only claims that are explicitly recommended for
    # retention and are not model outputs or old model arithmetic.
    history_links: dict[str, list[str]] = {}
    unmatched: list[pd.Series] = []
    for _, h in hist.iterrows():
        candidates = [(similarity(h.fact_or_dataset, d.dataset_or_field), d.asset_id)
                      for _, d in data.iterrows()]
        score, asset_id = max(candidates, default=(0.0, ""))
        if score >= 0.45:
            history_links.setdefault(asset_id, []).append(h.recovered_id)
        else:
            unmatched.append(h)

    rows = []
    for i, (_, d) in enumerate(data.iterrows(), start=1):
        nature = d.data_nature
        if d.direct_use_status == "NOT_EVIDENCE":
            record_type = "MODEL_ARTIFACT_NOT_EVIDENCE"
        elif d.direct_use_status == "NOT_DIRECT":
            record_type = "DERIVED_SCREEN_NOT_EVIDENCE"
        else:
            record_type = "EVIDENCE_ASSET"
        rows.append({
            "master_id": f"M{i:03d}",
            "origin_record_id": d.asset_id,
            "record_type": record_type,
            "category": d.category,
            "claim_or_dataset": d.dataset_or_field,
            "value": d.value,
            "unit": d.unit,
            "year": d.year,
            "geography": d.geography,
            "scope": d.scope,
            "data_nature": nature,
            "reliability": d.reliability_grade,
            "use_status": d.direct_use_status,
            "source_id": url_to_source.get(normalize_url(d.source_url), ""),
            "source_document": d.source_document,
            "source_locator": d.source_locator,
            "source_url": d.source_url,
            "local_path": d.file_path,
            "historical_crossref": ";".join(sorted(history_links.get(d.asset_id, []))),
            "current_paper_retained": d.current_paper_retained,
            "limitations": d.limitations,
            "potential_research_use": d.potential_research_use,
        })

    next_id = len(rows) + 1
    for h in unmatched:
        verdict = h.recommended_keep_or_reject.upper()
        if not verdict.startswith("KEEP") or "MODEL_OUTPUT" in h.data_nature or "MODEL_ARITHMETIC" in h.data_nature:
            continue
        artifact_tokens = ("MODEL_OUTPUT", "DERIVED_SCENARIO", "HISTORICAL_SENSITIVITY",
                           "DERIVED_OPTIMIZATION", "MODEL_ASSUMPTION", "MODEL_ARITHMETIC")
        nature_detail = (h.data_nature_detail or h.data_nature).upper()
        record_type = ("MODEL_ARTIFACT_NOT_EVIDENCE"
                       if any(token in nature_detail for token in artifact_tokens)
                       else "HISTORICAL_RECOVERY_ONLY")
        rows.append({
            "master_id": f"M{next_id:03d}",
            "origin_record_id": h.recovered_id,
            "record_type": record_type,
            "category": "historical_recovery",
            "claim_or_dataset": h.fact_or_dataset,
            "value": h.value,
            "unit": h.unit,
            "year": h.year,
            "geography": h.geography,
            "scope": "Plan/data fact recovered from prior manuscript lineage",
            "data_nature": h.data_nature_detail or h.data_nature,
            "reliability": h.evidence_reliability,
            "use_status": verdict,
            "source_id": "",
            "source_document": h.source_or_old_tex_location,
            "source_locator": h.source_or_old_tex_location,
            "source_url": h.source_url,
            "local_path": "",
            "historical_crossref": h.recovered_id,
            "current_paper_retained": h.current_0db06ec_status,
            "limitations": h.reason,
            "potential_research_use": h.reason,
        })
        next_id += 1

    frame = pd.DataFrame(rows)
    if frame.master_id.duplicated().any():
        raise ValueError("duplicate master IDs")
    frame.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(frame.groupby(["record_type", "use_status"]).size().to_string())
    print(f"wrote {len(frame)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
