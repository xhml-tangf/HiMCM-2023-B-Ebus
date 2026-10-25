"""Validate the model-independent evidence pack and write a file manifest."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    data = pd.read_csv(HERE / "data_asset_inventory.csv", dtype=str).fillna("")
    gaps = pd.read_csv(HERE / "data_gap_register.csv", dtype=str).fillna("")
    sources = pd.read_csv(HERE / "source_index.csv", dtype=str).fillna("")
    history = pd.read_csv(HERE / "historical_recovery.csv", dtype=str).fillna("")
    master = pd.read_csv(HERE / "evidence_master_register.csv", dtype=str).fillna("")
    questions = pd.read_csv(HERE / "research_question_support_matrix.csv", dtype=str).fillna("")

    if data.asset_id.duplicated().any():
        raise ValueError("duplicate data asset IDs")
    if sources.source_id.duplicated().any():
        raise ValueError("duplicate source IDs")
    if history.recovered_id.duplicated().any():
        raise ValueError("duplicate historical IDs")
    if questions.question_id.duplicated().any():
        raise ValueError("duplicate research-question IDs")
    if master.master_id.duplicated().any():
        raise ValueError("duplicate master IDs")
    if (master.record_type == "MODEL_ARTIFACT_NOT_EVIDENCE").any() and (
            master.loc[master.record_type == "MODEL_ARTIFACT_NOT_EVIDENCE", "use_status"]
            == "DIRECT").any():
        raise ValueError("model artifact was tagged directly usable")
    for _, row in master.iterrows():
        if row.record_type == "EVIDENCE_ASSET" and not row.source_document:
            raise ValueError(f"evidence without source document: {row.master_id}")
        if (row.record_type == "EVIDENCE_ASSET" and
                not (row.source_url or row.local_path or "No independent URL" in row.source_document)):
            raise ValueError(f"evidence without URL/path/provenance note: {row.master_id}")

    manifest_rows = []
    files = [
        ("evidence_master_register.csv", "统一证据主表", len(master)),
        ("data_asset_inventory.csv", "当前数据资产", len(data)),
        ("data_gap_register.csv", "缺口登记", len(gaps)),
        ("source_index.csv", "资料索引", len(sources)),
        ("historical_recovery.csv", "历史版本回收", len(history)),
        ("research_question_support_matrix.csv", "研究问题支持矩阵", len(questions)),
        ("README.md", "盘点总说明", ""),
        ("data_inventory_report.md", "数据清单报告", ""),
        ("source_index_report.md", "来源索引报告", ""),
        ("historical_version_diff.md", "历史论文差异报告", ""),
        ("research_capability_assessment.md", "证据能力评估", ""),
        ("evidence_decision_brief.md", "证据盘点结论简报", ""),
        ("previous_version_cc7deab/ebus_transition.tex", "上一版论文 TeX 快照", ""),
        ("previous_version_cc7deab/ebus_transition.pdf", "上一版论文 PDF 快照", ""),
    ]
    for name, purpose, rows in files:
        path = HERE / name
        if not path.exists():
            raise FileNotFoundError(path)
        manifest_rows.append(dict(file=name, purpose=purpose, rows=rows, sha256=sha(path)))
    pd.DataFrame(manifest_rows).to_csv(HERE / "evidence_pack_manifest.csv", index=False, encoding="utf-8-sig")
    print({
        "master": len(master), "evidence_assets": len(data), "gaps": len(gaps),
        "sources": len(sources), "historical": len(history), "research_questions": len(questions),
    })


if __name__ == "__main__":
    main()
