"""Save the current built-in editor's PDF output for local visual QA.

This never invokes a compiler. Run before compile_latex_document; only a new,
complete PDF with the canonical document's filename is copied from the
editor's transient output directory. The existing TeX editor stays open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--editor-cache", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=150)
    args = parser.parse_args()
    started = time.time()
    print("Waiting for the canonical document's built-in editor PDF", flush=True)
    while time.time() - started < args.timeout:
        for path in args.editor_cache.glob("preview-*/ebus_transition.pdf"):
            try:
                if path.stat().st_mtime < started:
                    continue
                data = path.read_bytes()
                if not data.rstrip().endswith(b"%%EOF"):
                    continue
                document = fitz.open(stream=data, filetype="pdf")
                pages = len(document)
                texts = [p.get_text() for p in document]
                document.close()
                output = ROOT / "paper/ebus_transition.pdf"
                output.write_bytes(data)
                source = ROOT / "paper/ebus_transition.tex"
                source_files = {
                    str(p.relative_to(source.parent)).replace("\\", "/"):
                    hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(source.parent.rglob("*"))
                    if p.is_file() and "archive" not in p.parts
                    and p.suffix.lower() in (".tex", ".bib", ".sty", ".png", ".jpg")
                }
                report = {
                    "producer": "built-in editor compiler; no separate compilation",
                    "pdf_sha256": hashlib.sha256(data).hexdigest(),
                    "main_tex_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "project_source_files_sha256": source_files,
                    "pages_including_ai_report": pages,
                    "ai_report_pages": [i + 1 for i, t in enumerate(texts)
                                        if "Report on Use of AI" in t.splitlines()],
                    "letter_heading_pages": [i + 1 for i, t in enumerate(texts)
                                             if "Subject:" in t and "decision" in t.lower()],
                }
                (ROOT / "results/editor_pdf_build.json").write_text(
                    json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print(f"Saved the editor PDF: {pages} pages; SHA-256 {report['pdf_sha256']}")
                return
            except (OSError, RuntimeError, ValueError):
                pass  # The compiler may still be writing or cleaning up.
        time.sleep(0.01)
    raise SystemExit("No complete new editor PDF was observed; nothing was exported")


if __name__ == "__main__":
    main()
