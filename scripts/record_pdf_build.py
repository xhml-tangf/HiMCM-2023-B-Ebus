"""Record hashes and pagination for the canonical compiled PDF."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "paper/ebus_transition.pdf"
TEX = ROOT / "paper/ebus_transition.tex"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    document = fitz.open(PDF)
    texts = [page.get_text() for page in document]
    source_files = {
        str(path.relative_to(TEX.parent)).replace("\\", "/"): sha256(path)
        for path in sorted(TEX.parent.rglob("*"))
        if path.is_file()
        and "archive" not in path.parts
        and path.suffix.lower() in (".tex", ".bib", ".sty", ".png", ".jpg")
    }
    ai_pages = [
        i + 1 for i, text in enumerate(texts)
        if "Report on Use of AI" in text.splitlines()
    ]
    letter_pages = [
        i + 1 for i, text in enumerate(texts)
        if "Subject:" in text and "decision" in text.lower()
    ]
    report = {
        "producer": (
            "OpenAI Codex app-owned Tectonic 0.17.0 using the editor cache; "
            "the built-in editor compiler returned success for the same source"
        ),
        "pdf_sha256": sha256(PDF),
        "main_tex_sha256": sha256(TEX),
        "project_source_files_sha256": source_files,
        "pages_including_ai_report": len(document),
        "ai_report_pages": ai_pages,
        "letter_heading_pages": letter_pages,
    }
    (ROOT / "results/editor_pdf_build.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "results/local_editor_compile.json").write_text(
        json.dumps({
            "producer": "app-owned Tectonic 0.17.0 using the editor cache",
            "pdf_sha256": report["pdf_sha256"],
            "main_tex_sha256": report["main_tex_sha256"],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
