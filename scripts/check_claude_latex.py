"""Check and render the native LaTeX reconstruction without changing models."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "paper/claude_plan/latex"
OUT = ROOT / "tmp/claude_latex_qa"


def main() -> None:
    OUT.mkdir(exist_ok=True, parents=True)
    pdf = PROJECT / "main.pdf"
    doc = fitz.open(pdf)
    texts = [unicodedata.normalize("NFKC", p.get_text()) for p in doc]
    errors = []
    ai = [i + 1 for i, t in enumerate(texts) if "Report on Use of AI" in t.splitlines()]
    solution_pages = ai[0] - 1 if len(ai) == 1 else len(doc)
    if len(ai) != 1:
        errors.append("AI report start not uniquely identified")
    if solution_pages > 25:
        errors.append("solution exceeds 25 pages")
    if [i + 1 for i, t in enumerate(texts) if "Keywords:" in t] != [1]:
        errors.append("summary does not fit on page one")
    letter_start = [i + 1 for i, t in enumerate(texts) if "Dear Transportation Officials," in t]
    letter_end = [i + 1 for i, t in enumerate(texts) if "Sincerely," in t]
    if len(letter_start) != 1 or letter_start != letter_end:
        errors.append("letter does not fit on one page")
    all_text = "\n".join(texts)
    if "??" in all_text or "[?]" in all_text:
        errors.append("unresolved references")
    log = (PROJECT / "main.log").read_text(encoding="utf-8", errors="replace")
    if "Overfull" in log or "undefined" in log.lower():
        errors.append("overfull boxes or undefined references in compiler log")
    for i, page in enumerate(doc):
        if abs(page.rect.width - 595.28) > 1 or abs(page.rect.height - 841.89) > 1:
            errors.append(f"page {i+1} is not A4")
        if "Team #" not in texts[i]:
            errors.append(f"page {i+1} missing team-number header")
        if i < solution_pages and f"Page {i+1} of {solution_pages}" not in texts[i]:
            errors.append(f"page {i+1} has incorrect header pagination")
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    if x0 < 43 or x1 > page.rect.width-43 or y0 < 15 or y1 > page.rect.height-38:
                        errors.append(f"page {i+1}: text beyond safe bounds: {span['text'][:35]}")
                    if "\ufffd" in span["text"]:
                        errors.append(f"page {i+1}: replacement character")
        page.get_pixmap(dpi=105, alpha=False).save(OUT / f"page-{i+1:02d}.png")
    for start in range(0, len(doc), 8):
        sheet = Image.new("RGB", (4*340, 2*485), "#dce1e4")
        draw = ImageDraw.Draw(sheet)
        for n in range(start, min(start+8, len(doc))):
            with Image.open(OUT / f"page-{n+1:02d}.png") as img:
                img.thumbnail((330, 460))
                x, y = (n-start) % 4 * 340 + 5, (n-start) // 4 * 485 + 21
                sheet.paste(img, (x, y))
                draw.text((x, y-17), f"Page {n+1}", fill="black")
        sheet.save(OUT / f"contact-{start//8+1}.jpg", quality=92)
    source_urls = set()
    for path in (PROJECT / "sections").glob("*.tex"):
        source_urls.update(re.findall(r"\\href\{([^}]+)\}", path.read_text(encoding="utf-8")))
    pdf_urls = {link.get("uri") for page in doc for link in page.get_links() if link.get("uri")}
    if source_urls - pdf_urls:
        errors.append("some source links missing from PDF")
    report = {
        "total_pages": len(doc), "solution_pages": solution_pages,
        "ai_report_pages": len(doc)-solution_pages, "letter_pages": letter_start,
        "summary_pages": [1], "within_25_solution_pages": solution_pages <= 25,
        "automatic_layout_pass": not errors, "errors": errors,
        "compiler": "Tectonic 0.17.0; editor compile separately confirmed",
        "source_files_sha256": {str(p.relative_to(PROJECT)).replace("\\", "/"):
                                hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(PROJECT.rglob("*"))
                                if p.suffix in (".tex", ".png")},
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "visual_review": "pending image inspection",
    }
    (PROJECT / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_files_sha256"}, indent=2))


if __name__ == "__main__":
    main()
