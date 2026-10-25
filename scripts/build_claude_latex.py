"""Reconstruct the executed Claude-plan manuscript as a portable LaTeX project.

The Markdown manuscript remains the content snapshot. This exporter replaces
its manually paginated contents, ASCII mathematics and tables with native TeX.
It does not rerun or change the scheduling/accounting models.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper/claude_plan/charging_ahead_claude_plan.md"
OUT = ROOT / "paper/claude_plan/latex"

MATH = [
    r"""\begin{align}
B_{\mathrm{use}}&=\varepsilon R, & B&=B_{\mathrm{use}}/u,\\
P_{\mathrm{battery}}&=60B_{\mathrm{use}}/T, &
P_{\mathrm{grid}}&=P_{\mathrm{battery}}/\eta .
\end{align}""",
    r"""\noindent\textbf{Direct connection $i\to j$.}
\begin{align}
e_i+\tau(d_i,o_j)&\le s_j,\\
u_i+w(d_i,o_j)+\ell_j&\le R,\\
u_j&=u_i+w(d_i,o_j)+\ell_j.
\end{align}""",
    r"""\noindent\textbf{Connection through a charger $c\in S$.}
\begin{align}
u_i+w(d_i,c)&\le R,\\
e_i+\tau(d_i,c)+T+\tau(c,o_j)&\le s_j,\\
w(c,o_j)+\ell_j&\le R,\\
u_j&=w(c,o_j)+\ell_j.
\end{align}""",
    r"""\begin{align}
N_d&=n-|M^*|,\\
\mathrm{PVR}&=\max_t\bigl|\{i:s_i\le t<e_i\}\bigr|,\\
N_e&\ge N_d\ge\mathrm{PVR}.
\end{align}
Here $M^*$ is a maximum matching; the last inequality chain uses metric travel times.""",
    r"""\begin{equation}
w(c_{\mathrm{prev}},o_b)+L_b+w(d_b,c_{\mathrm{next}})\le R.
\end{equation}
Here $L_b$ includes the service and internal deadhead distance of block $b$.""",
    r"""\begin{align}
E_{\mathrm{grid}}&=(D_{\mathrm{service}}+D_{\mathrm{deadhead}})\varepsilon/\eta,\\
G_{d,\mathrm{op}}&=D_{\mathrm{diesel}}\,\mathrm{EF}_{\mathrm{diesel}},\\
G_{e,\mathrm{op},t}&=E_{\mathrm{grid},t}\gamma_t,\\
G_{\mathrm{battery},0}&=N_e B e_{\mathrm{battery}}.
\end{align}""",
    r"""\begin{align}
C_e^{\mathrm{cap}}&=N_e(c_{\mathrm{body}}+B c_{\mathrm{battery}})+C_{\mathrm{infra}},\\
C_{\mathrm{eligible}}&=\max\{0,C_e^{\mathrm{cap}}-C_d^{\mathrm{cap}}\},\\
G_{\mathrm{grant}}&=\phi C_{\mathrm{eligible}},\qquad 0\le\phi\le0.50,\\
\mathrm{NPV}(\phi)&=\mathrm{PV}_d-\mathrm{PV}_{e,\mathrm{gross}}
                       +\phi C_{\mathrm{eligible}}.
\end{align}""",
    r"""\begin{align}
\phi^*&=\max\left\{0,\frac{\mathrm{PV}_{e,\mathrm{gross}}-\mathrm{PV}_d}
                             {C_{\mathrm{eligible}}}\right\},
\quad C_{\mathrm{eligible}}>0,\\
\mathrm{TCO}_v&=\frac{\text{discounted net cost of fleet }v}
                        {\text{discounted vehicle-km of fleet }v}.
\end{align}
If eligible cost is zero, the grant cannot close a positive present-cost gap.""",
    r"""\begin{align}
\mathrm{score}_r&=\frac{D_{r,\mathrm{service}}}{N_{e,r}}
                         \frac{N_{d,r}}{N_{e,r}},\\
\mathcal R_y&=\text{first }\left\lceil |\mathcal R|y/10\right\rceil
                           \text{ routes in descending score order},\\
\mathrm{stock}_y&=\max\{\mathrm{stock}_{y-1},N_e(\mathcal R_y)\}.
\end{align}""",
]

# Captions and relative column widths follow the source table order.
TABLES = [
    ("Case-study eligibility and evidence boundaries", [0.16, 0.47, 0.37]),
    ("Scheduling inputs, assumptions and evidence status", [0.23, 0.37, 0.40]),
    ("Independent validation and small-instance optimality comparisons", [0.33, 0.35, 0.32]),
    ("Vancouver service patterns and independently validated active fleets", [.115, .205, .16, .135, .13, .135, .12]),
    ("Selected mathematical charging nodes and peak simultaneous charge counts", [.22, .57, .21]),
    ("Vancouver travel, electricity and charger requirements", [.34, .27, .39]),
    ("Fleet response to alternate distance assumptions", [.30, .22, .48]),
    ("Avoided diesel exhaust pollutants under transferred factor ranges", [.24, .28, .48]),
    ("Financial inputs and their evidence status", [.30, .34, .36]),
    ("Immediate-replacement financial outcomes by grant share", [.16, .20, .22, .23, .19]),
    ("Illustrative Vancouver route conversion and gross annual investment", [.13, .13, .17, .20, .14, .23]),
    ("Vancouver staged grants, agency capital and battery replacement (CAD million)", [.12, .21, .21, .21, .25]),
    ("Representative-day scheduling results across the three cities", [.37, .21, .21, .21]),
    ("Comparator financial and ecological screens under common transferred parameters", [.46, .27, .27]),
    ("Comparator annual purchases, residual diesel fleets and gross investment", [.11, .14, .14, .15, .15, .14, .17]),
    ("Separate inventory-cohort renewal comparison", [.39, .305, .305]),
    ("Requirement coverage and remaining evidence gaps", [.31, .25, .44]),
]

PREAMBLE = r"""% Reconstructed from the executed manuscript; no model results changed.
% Compile with XeLaTeX, LuaLaTeX or Tectonic. See README.md.
\documentclass[12pt,a4paper]{article}
\usepackage[margin=19mm,headheight=15pt,headsep=7mm]{geometry}
\usepackage{amsmath,amssymb,booktabs,longtable,array,graphicx}
\usepackage{lmodern,fancyhdr,placeins}
\usepackage[hidelinks,bookmarksnumbered]{hyperref}
\input{team.tex}
\hypersetup{pdftitle={Charging Ahead: A Two-Constant, Timetable-Preserving Transition},
  pdfauthor={},pdfsubject={2023 HiMCM Problem B; retrospective modeling study}}
\setlength{\parindent}{1.2em}
\setlength{\parskip}{3pt}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.08}
\setlength{\LTpre}{7pt}
\setlength{\LTpost}{7pt}
\setlength{\emergencystretch}{1.8em}
\setcounter{tocdepth}{2}
\renewcommand{\thesection}{\Roman{section}}
\renewcommand{\thesubsection}{\thesection.\Alph{subsection}}
\makeatletter
\renewcommand*{\l@section}{\@dottedtocline{1}{0em}{3em}}
\renewcommand*{\l@subsection}{\@dottedtocline{2}{1.5em}{4.1em}}
\makeatother
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{Team \#\TeamNumber}
\fancyhead[R]{Page \thepage\ of \pageref{LastSolutionPage}}
\renewcommand{\headrulewidth}{0.4pt}
\fancypagestyle{plain}{\fancyhf{}\fancyhead[L]{Team \#\TeamNumber}
  \fancyhead[R]{Page \thepage\ of \pageref{LastSolutionPage}}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcommand{\NeedRoom}[1]{\par\begingroup
  \dimen0=#1\baselineskip\relax
  \ifdim\pagegoal<\maxdimen
    \ifdim\dimexpr\pagegoal-\pagetotal\relax<\dimen0\newpage\fi
  \fi\endgroup}
\begin{document}
"""


def escape(text: str) -> str:
    text = html.unescape(text)
    substitutions = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
                     "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
                     "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(substitutions.get(c, c) for c in text)


def inline(text: str) -> str:
    """Escape prose, restoring only explicitly recognized math and citations."""
    tokens: list[str] = []

    def save(value: str) -> str:
        tokens.append(value)
        return f"ZZTOKEN{len(tokens)-1}ZZ"

    text = html.unescape(text)
    text = re.sub(r"\[Source\]\(([^)]+)\)", lambda m: save(r"\href{" + m[1] + r"}{[Online]}"), text)
    text = re.sub(r"\[(\d+)\]", lambda m: save(r"\cite{ref" + m[1] + "}"), text)
    math_tokens = {
        "N_d": r"$N_d$", "N_e": r"$N_e$", "CO2e": r"CO$_2$e",
        "o_i": r"$o_i$", "d_i": r"$d_i$", "s_i": r"$s_i$", "e_i": r"$e_i$",
        "ell_i": r"$\ell_i$", "u_i": r"$u_i$", "C(v)": r"$\mathrm{C}(v)$",
        "NOx": r"NO$_x$", "PM2.5": r"PM$_{2.5}$", "phi_star": r"$\phi^*$",
        "R = 270 km": r"$R=270$ km", "T = 60 min": r"$T=60$ min",
        "R = 10 km": r"$R=10$ km", "T = 5 min": r"$T=5$ min",
        "R = infinity": r"$R=\infty$", "K <= 4": r"$K\le4$",
    }
    pattern = "|".join(re.escape(k) for k in sorted(math_tokens, key=len, reverse=True))
    text = re.sub(pattern, lambda m: save(math_tokens[m[0]]), text)
    text = escape(text)
    for n, token in enumerate(tokens):
        text = text.replace(f"ZZTOKEN{n}ZZ", token)
    return text


def parse_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.startswith("# "):
            sections.append((line[2:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
    return sections


def render_table(rows: list[list[str]], index: int) -> str:
    caption, ratios = TABLES[index]
    headers, data = rows[0], rows[1:]
    if index == 3:
        headers = ["Pattern", "Date", "Trips", "N_d", "PVR", "N_e", "Days"]
    elif index == 9:
        headers = ["Grant share", "Grant (CAD m)", "Agency PV (CAD bn)", "NPV savings (CAD m)", "Payback year"]
    elif index == 10:
        headers = ["Year", "Routes", "New BEBs", "Electric stock", "Diesel", "Gross (CAD m)"]
    elif index == 11:
        headers = ["Year", "Grant 25%", "Grant 50%", "Agency 50%", "Battery replace- ment"]
    elif index == 14:
        headers = ["Year", "CTA new EV", "CTA diesel", "CTA gross (m)", "London new EV", "London diesel", "London gross (m)"]
    widths = [r"L{\dimexpr " + f"{v/sum(ratios):.5f}" + r"\textwidth-2\tabcolsep\relax}" for v in ratios]
    head = " & ".join(r"\textbf{" + inline(v) + "}" for v in headers) + r" \\"
    result = [r"\begin{longtable}{@{}" + "".join(widths) + "@{}}",
              r"\caption{" + inline(caption) + r"}\label{tab:source" + str(index+1) + r"}\\",
              r"\toprule", head, r"\midrule", r"\endfirsthead",
              r"\multicolumn{" + str(len(headers)) + r"}{l}{Table \thetable\ (continued)}\\",
              r"\toprule", head, r"\midrule", r"\endhead",
              r"\midrule\multicolumn{" + str(len(headers)) + r"}{r}{Continued on next page}\\\endfoot",
              r"\bottomrule\endlastfoot"]
    result.extend(" & ".join(inline(v) for v in row) + r" \\" for row in data)
    result.append(r"\end{longtable}")
    return "\n".join(result)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sections").mkdir(exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    if not (OUT / "team.tex").exists():
        (OUT / "team.tex").write_text("% Replace only the argument below with your actual control number.\n"
                                      "\\newcommand{\\TeamNumber}{\\underline{\\hspace{23mm}}}\n", encoding="utf-8")
    sections = parse_sections(SOURCE.read_text(encoding="utf-8"))
    table_index = equation_index = figure_count = 0
    files: list[str] = []
    ref_entries: list[tuple[str, str]] = []
    ref_notes: list[str] = []
    for title, lines in sections:
        if title == "Contents":
            continue
        if title.startswith("References:"):
            for line in lines:
                m = re.match(r"\[(\d+)\] (.*)", line)
                if m:
                    ref_entries.append((m[1], m[2]))
                elif line.strip():
                    ref_notes.append(inline(line))
            continue
        is_summary = title == "Summary Sheet"
        is_ai = title == "Report on Use of AI"
        is_letter = title.startswith("X.")
        if is_summary:
            result = [r"\begin{center}",
                      r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}ccc}",
                      r"Problem Chosen & 2023 & Team Control Number\\",
                      r"{\Large\bfseries B} & {\Large\bfseries HiMCM} & {\Large\bfseries\TeamNumber}\\",
                      r"\end{tabular*}", r"\vspace{9pt}", r"{\Large\bfseries Summary Sheet}",
                      r"\end{center}\hrule\vspace{8pt}"]
        elif is_ai:
            result = [r"\clearpage", r"\fancyhead[R]{AI Report -- Page \thepage}",
                      r"\section*{Report on Use of AI}"]
        else:
            clean = re.sub(r"^[IVX]+(?:\.[AB])?\.\s*", "", title)
            is_subsection = bool(re.match(r"^[IVX]+\.[AB]\.", title))
            result = ([r"\clearpage"] if is_letter else []) + [
                r"\NeedRoom{10}",
                (r"\subsection{" if is_subsection else r"\section{") + escape(clean) + "}"]
            if is_letter:
                result.append(r"\begingroup\setlength{\parindent}{0pt}\setlength{\parskip}{7pt}")
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            if line.startswith("|"):
                rows = []
                while i < len(lines) and (lines[i].startswith("|") or not lines[i].strip()):
                    row = lines[i]
                    if row.startswith("|"):
                        cells = [x.strip() for x in row.strip().strip("|").split("|")]
                        if not all(re.fullmatch(r":?-+:?", x) for x in cells):
                            rows.append(cells)
                    i += 1
                result.append(render_table(rows, table_index))
                table_index += 1
                continue
            if line.startswith("    "):
                while i < len(lines) and lines[i].startswith("    "):
                    i += 1
                result.append(MATH[equation_index])
                equation_index += 1
                continue
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            if m:
                caption = re.sub(r"^Figure \d+\.\s*", "", m[1])
                original = (SOURCE.parent / m[2]).resolve()
                shutil.copy2(original, OUT / "images" / original.name)
                figure_count += 1
                result += [r"\begin{figure}[htbp]\centering",
                           r"\includegraphics[width=\textwidth,height=0.37\textheight,keepaspectratio]{images/" + original.name + "}",
                           r"\caption{" + inline(caption) + r"}\label{fig:result" + str(figure_count) + "}",
                           r"\end{figure}"]
            elif is_summary and line.startswith("Charging Ahead:"):
                result += [r"\begin{center}{\Large\bfseries " + escape(line) + r"}\end{center}"]
            elif is_summary and line.startswith("Modeling solution for"):
                result.append(r"\begin{center}Modeling solution for 2023 HiMCM Problem B\\"
                              r"Retrospective study; LaTeX reconstruction, 24 October 2026\end{center}")
            elif is_ai and line == "No external 2023 HiMCM solution manuscript was used.":
                result.append("Public Outstanding papers were consulted only for layout conventions.")
            elif is_letter and line == "Sincerely,The Modeling Team":
                result.append(r"Sincerely,\\The Modeling Team")
            else:
                if is_ai:
                    line = line.replace("No external 2023 HiMCM solution manuscript was used.",
                                        "Public 2023 Outstanding papers were consulted only for layout conventions; their models, results and prose were not incorporated.")
                    line = line.replace("The current session used deepseek-flash; earlier turns in the same thread were labeled GPT-6.",
                                        "Implementation sessions were recorded as deepseek-flash; earlier turns in the same thread were labeled GPT-6.")
                result.append(inline(line) + "\n")
            i += 1
        if is_letter:
            result.append(r"\endgroup")
        if title.startswith("II."):
            result.append(r"""\subsection*{Principal notation}
\begin{longtable}{@{}L{0.22\textwidth}L{0.70\textwidth}@{}}
\caption{Principal notation and units}\label{tab:notation}\\
\toprule Symbol & Meaning and units\\\midrule
$i,j;\ n$ & Trip indices; total scheduled trips.\\
$o_i,d_i;\ s_i,e_i$ & Origin and destination; departure and arrival (minutes).\\
$\ell_i;\ u_i$ & Service distance; distance since the last full charge (km).\\
$w(a,b);\ \tau(a,b)$ & Deadhead distance (km) and travel time (minutes).\\
$R;\ T$ & Usable range (km); fixed charge duration (minutes).\\
$S;\ K$ & Selected charging nodes; node-count limit.\\
$N_d,N_e;\ \mathrm{PVR}$ & Diesel minimum, feasible electric fleet, concurrent-trip lower bound.\\
$\varepsilon;\ \eta;\ u$ & Battery kWh/km; charging efficiency; usable battery fraction.\\
$\gamma_t;\ \phi$ & Grid kgCO$_2$e/kWh; eligible-capital grant share.\\
\bottomrule
\end{longtable}
The state $u_i$ and the battery fraction $u$ are distinct quantities.""")
        if is_ai:
            result.append(inline("Formatting update, 24 October 2026: a Codex assistant converted this manuscript into native LaTeX, typeset equations and checked the resulting PDF. The exact current model version and a complete transcript export have not been independently recorded. This formatting step does not resolve the missing original AI conversations.") + "\n")
        filename = "summary.tex" if is_summary else ("ai_report.tex" if is_ai else f"section_{len(files):02d}.tex")
        (OUT / "sections" / filename).write_text("\n\n".join(result) + "\n", encoding="utf-8")
        files.append(filename)
    assert table_index == len(TABLES), (table_index, len(TABLES))
    assert equation_index == len(MATH), (equation_index, len(MATH))
    refs = [r"\clearpage\phantomsection\addcontentsline{toc}{section}{References}",
            r"\begin{thebibliography}{99}\raggedright"]
    for key, text in ref_entries:
        refs.append(r"\bibitem{ref" + key + "} " + inline(text))
    refs += [r"\end{thebibliography}", *ref_notes, r"\label{LastSolutionPage}"]
    (OUT / "sections/references.tex").write_text("\n\n".join(refs) + "\n", encoding="utf-8")
    inputs = [PREAMBLE]
    for filename in files:
        if filename == "ai_report.tex":
            inputs.append(r"\FloatBarrier\input{sections/references.tex}")
        inputs.append(r"\input{sections/" + filename + "}")
        if filename == "summary.tex":
            inputs.append(r"\clearpage\tableofcontents\clearpage")
    inputs.append(r"\end{document}")
    (OUT / "main.tex").write_text("\n".join(inputs) + "\n", encoding="utf-8")
    manifest = {"source": str(SOURCE.relative_to(ROOT)),
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "source_sections": len(sections), "tables_converted": table_index,
                "equation_groups_converted": equation_index, "figures_copied": figure_count,
                "references_converted": len(ref_entries),
                "content_changes": ["Automatic contents instead of old page numbers",
                                    "Added notation table; native mathematical typesetting",
                                    "Corrected AI appendix statement about format-only exemplars",
                                    "Documented October 24 formatting assistance",
                                    "Defined zero-eligible-cost case for the existing subsidy formula"]}
    (OUT / "conversion_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
