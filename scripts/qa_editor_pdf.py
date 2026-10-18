"""Check and render the PDF produced by the built-in editor; never compile."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    pdf = ROOT / "paper/ebus_transition.pdf"
    document = fitz.open(pdf)
    texts = [page.get_text() for page in document]
    ai = [i + 1 for i, text in enumerate(texts) if "AI Use Report" in text.splitlines()]
    summary = [i + 1 for i, text in enumerate(texts) if "Keywords:" in text]
    letter_start = [i + 1 for i, text in enumerate(texts) if "Dear decision-makers," in text]
    letter_end = [i + 1 for i, text in enumerate(texts) if "Sincerely," in text]
    issues = []
    solution_pages = ai[0] - 1 if ai else len(document)
    if solution_pages > 25:
        issues.append("solution exceeds 25 pages")
    if summary != [1]:
        issues.append("summary does not fit on first page")
    if len(letter_start) != 1 or letter_start != letter_end:
        issues.append("letter is not contained on one page")
    source = (ROOT / "paper/ebus_transition.tex").read_text(encoding="utf-8")
    source_urls = set(re.findall(r"\\href\{([^}]+)\}", source))
    pdf_urls = {link["uri"] for page in document for link in page.get_links() if link.get("uri")}
    if source_urls - pdf_urls:
        issues.append("external source hyperlinks missing from PDF")
    output_dir = ROOT / "tmp/pdf_layout_review"
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(document):
        if f"Page {i+1}" not in texts[i]:
            issues.append(f"page {i+1} missing expected header")
        if "[?]" in texts[i] or "??" in texts[i]:
            issues.append(f"unresolved reference on page {i+1}")
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    if x0 < 52 or x1 > page.rect.width - 52 or y0 < 0 or y1 > page.rect.height:
                        issues.append(f"text outside expected boundaries on page {i+1}")
        page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4)).save(output_dir / f"page-{i+1:02d}.png")
    for start in range(0, len(document), 6):
        contact = Image.new("RGB", (1040, 2040), "#d8d8d8")
        draw = ImageDraw.Draw(contact)
        for j, number in enumerate(range(start + 1, min(start + 7, len(document) + 1))):
            image = Image.open(output_dir / f"page-{number:02d}.png").convert("RGB")
            image.thumbnail((500, 650))
            x = 10 + (j % 2) * 520
            y = 25 + (j // 2) * 680
            contact.paste(image, (x, y))
            draw.text((x, y-17), f"Page {number}", fill="black")
        contact.save(output_dir / f"contact-{start//6+1}.png")
    report = {"pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
              "total_pages": len(document), "solution_pages": solution_pages,
              "ai_report_pages": ai,
              "external_source_hyperlinks_verified": len(source_urls & pdf_urls),
              "summary_pages": summary, "letter_pages": letter_start,
              "issues": sorted(set(issues)),
              "note": "Geometry/pagination checks and rendered pages do not certify research completeness; visual inspection is recorded separately."}
    (ROOT / "results/pdf_layout_checks.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
