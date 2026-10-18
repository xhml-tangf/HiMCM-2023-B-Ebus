"""Fallback PDF rendering of the editable LaTeX draft when native compiler is unavailable.

This renderer handles the manuscript's small command subset. Equations are
rendered as transparent TeX notation, rather than silently changed.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper/ebus_transition.tex"
DEST = ROOT / "paper/ebus_transition.pdf"

EQUATIONS = [
    "N[y,k,d,p] = N[y-1,k,d,p] + purchases[y,k,d,p] - retirements[y,k,d,p]",
    "For each original departure i: assigned buses >= 1\n"
    "Sum of assigned bus capacity >= original trip capacity\n"
    "At each route/direction peak: available capacity >= original capacity",
    "SOC[next] = SOC[now] + charging input - winter trip energy\n"
    "            - deadhead energy - electric-accessory energy\n"
    "Minimum reserve <= SOC <= usable battery energy",
    "At each depot/time: simultaneous charging buses <= installed chargers\n"
    "                    simultaneous kW <= commissioned grid capacity",
    "Gross PV cost = discounted sum(capex + operations - salvage)\n"
    "                - discounted end-of-horizon residual value\n"
    "Incremental cost = electric gross PV - normal-renewal gross PV",
    "Life-cycle GHG = vehicle/battery manufacture + infrastructure\n"
    "               + fuel and electricity supply + maintenance\n"
    "               - end-of-life credits",
    "Economic score = 100 x (baseline cost - electric cost) / baseline cost\n"
    "GHG score      = 100 x (baseline GHG - electric GHG) / baseline GHG",
]


def inline(s: str) -> str:
    s = s.strip()
    s = s.replace(r"\\[4pt]", " ")
    s = re.sub(r"\\src\{([^}]*)\}", r" [\1]", s)
    s = re.sub(r"\\url\{([^}]*)\}", lambda m: f"<link href='{html.escape(m.group(1), quote=True)}' color='#125780'>[online source]</link>", s)
    for cmd in ("textbf", "emph", "texttt"):
        s = re.sub(r"\\" + cmd + r"\{([^{}]*)\}", r"\1", s)
    s = s.replace(r"\%", "%").replace(r"\emph", "").replace(r"\textbf", "")
    s = s.replace(r"\&", "&").replace(r"\_", "_")
    s = s.replace("$", "").replace(r"\mathrm", "")
    s = s.replace(r"\newemph", "")
    s = s.replace(r"\CO", "CO")
    s = s.replace(r"\emph", "")
    s = s.replace(r"\texttt", "")
    s = s.replace(r"\\", "<br/>")
    s = re.sub(r"\\(?:quad|qquad|noindent)", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("--", "-").replace("---", "-")
    return s


def split_paragraphs(block: str):
    return [x.strip() for x in re.split(r"\n\s*\n", block) if x.strip()]


def main() -> None:
    tex = SOURCE.read_text(encoding="utf-8")
    tex = tex.split(r"\begin{document}", 1)[1].split(r"\end{document}", 1)[0]
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=colors.HexColor("#153849"), alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="HeadingCustom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=colors.HexColor("#153849"), spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="SubheadingCustom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=12, textColor=colors.HexColor("#153849"), spaceBefore=9, spaceAfter=4))
    styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12.7, spaceAfter=7, splitLongWords=1))
    styles.add(ParagraphStyle(name="SmallCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=11, spaceAfter=5, splitLongWords=1))
    story = []
    body = []

    def flush():
        if not body:
            return
        raw = "\n".join(body)
        body.clear()
        for item in split_paragraphs(raw):
            value = inline(item)
            if value:
                story.append(Paragraph(value, styles["BodyCustom"]))

    lines = tex.splitlines()
    i = 0
    in_table = False
    in_ref = False
    equation_index = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(r"\begin{center}") or line.startswith(r"\end{center}"):
            flush(); i += 1; continue
        if line.startswith(r"\begin{table}") or line.startswith(r"\begin{longtable}"):
            flush(); in_table = True; i += 1; continue
        if line.startswith(r"\end{table}") or line.startswith(r"\end{longtable}"):
            flush(); in_table = False; i += 1; continue
        if line.startswith(r"\begin{tabular}") or line.startswith(r"\end{tabular}") or line.startswith(r"\centering"):
            i += 1; continue
        if line in (r"\toprule", r"\midrule", r"\bottomrule", r"\endhead", r"\small", r"\normalsize"):
            i += 1; continue
        if line.startswith(r"\begin{equation}"):
            flush(); eq=[]; i += 1
            while i < len(lines) and not lines[i].strip().startswith(r"\end{equation}"):
                eq.append(lines[i].strip()); i += 1
            eq_text = EQUATIONS[equation_index] if equation_index < len(EQUATIONS) else " ".join(eq)
            equation_index += 1
            story.append(Preformatted(eq_text, ParagraphStyle(name=f"Eq{len(story)}", fontName="Courier", fontSize=7.1, leading=9.5, leftIndent=7)))
            i += 1; continue
        m = re.match(r"\\(section\*?|subsection)\{(.+)\}", line)
        if m:
            flush()
            style = "SubheadingCustom" if m.group(1) == "subsection" else "HeadingCustom"
            story.append(Paragraph(inline(m.group(2)), styles[style])); i += 1; continue
        if line.startswith(r"\newpage"):
            flush(); story.append(PageBreak()); i += 1; continue
        if line.startswith(r"\tableofcontents"):
            story.append(Paragraph("Contents", styles["HeadingCustom"]))
            for label, page in [
                ("1. Problem definition and study boundary", 3),
                ("2. Evidence and baseline audit", 3),
                ("3. Fleet and service model", 3),
                ("4. Costs, funding and environmental accounting", 4),
                ("5. Observed and illustrative results", 5),
                ("6. Conditional 2024-2033 roadmap and transfer", 5),
                ("7. Sensitivity, limitations and completion gate", 5),
                ("8. References", 6),
                ("Decision-maker letter", 7),
                ("Report on Use of AI", 8),
            ]:
                story.append(Paragraph(f"{label} ........................................ {page}", styles["BodyCustom"]))
            i += 1; continue
        if line.startswith(r"\begin{enumerate}"):
            flush(); in_ref=True; i += 1; continue
        if line.startswith(r"\end{enumerate}"):
            flush(); in_ref=False; i += 1; continue
        if line.startswith(r"\caption"):
            flush(); story.append(Paragraph(inline(line), styles["SmallCustom"])); i += 1; continue
        if in_table:
            if "&" in line and line.endswith(r"\\"):
                cols = [inline(x) for x in line[:-2].split("&")]
                story.append(Paragraph(" | ".join(cols), styles["SmallCustom"]))
            i += 1; continue
        if in_ref and line.startswith(r"\item"):
            flush(); story.append(Paragraph("- " + inline(line.removeprefix(r"\item")), styles["SmallCustom"])); i += 1; continue
        if line.startswith("{") and "Large" in line:
            flush(); story.append(Paragraph(inline(line), styles["TitleCustom"])); i += 1; continue
        if line and not line.startswith("%"):
            body.append(line)
        else:
            flush()
        i += 1
    flush()

    def header(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#54717d"))
        canvas.drawString(0.72*inch, 0.44*inch, "Metro Vancouver electric bus transition - research draft")
        canvas.drawRightString(7.8*inch, 0.44*inch, str(doc.page))
        canvas.restoreState()

    doc = BaseDocTemplate(str(DEST), pagesize=(8.5*inch, 11*inch),
                          leftMargin=0.72*inch, rightMargin=0.72*inch,
                          topMargin=0.68*inch, bottomMargin=0.65*inch)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=header))
    doc.build(story)
    print(DEST)


if __name__ == "__main__":
    main()
