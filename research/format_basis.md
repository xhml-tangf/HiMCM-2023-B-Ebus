# LaTeX format basis and verification boundary

Checked 16 October 2026. This is a 2023 HiMCM **practice** manuscript, not a current contest submission.

## Reference availability

- [COMAP's 2025 HiMCM results](https://www.contest.comap.org/highschool/contests/himcm/2025results.html) identify eight Outstanding teams, including three for Problem B. They list winners, not downloadable full manuscripts. Searches for those teams' complete papers did not locate a verifiable public copy. Therefore this document does **not** claim to reproduce a 2025 winner's exact typography.
- A follow-up query on 18 October 2026 using the three 2025 Problem B control numbers likewise returned the official results page and derivative commentary, not an accessible paper file. The format check therefore uses the public 2024 examples plus the current official rules, and labels that evidence boundary explicitly.
- [COMAP's publicly posted 2024 HiMCM examples](https://www.comap.org/images/contests/2024_HiMCM_Examples.pdf) were inspected for visible conventions only: a distinct first-page Summary Sheet, team control number, problem letter, title, page headers and readable numbered sections. The example PDF combines excerpts from several papers, so its typography is not one mandatory template.
- COMAP's 2024 HiMCM flyer/overview includes a public Summary Sheet excerpt from an Outstanding Problem B team; it supports the same visible conventions but is not a full manuscript. See `research/outstanding_format_findings.md` for the verified control-number cross-checks.
- [COMAP's current official instructions](https://www.contest.comap.org/highschool/contests/himcm/instructions.html) provide the hard format rules: English PDF, at least 12-point type; team control number and page number at the top of every solution page; Summary Sheet first; at most 25 pages including contents, references and appendices; no student, advisor or institution names; AI use report after the 25-page solution. Use the competition-year instructions again before any actual submission because rules can change.

## Fixed design decisions in `paper/ebus_transition.tex`

1. `article` class, US Letter, 12-point Latin Modern, 0.80-inch margins. No small-font overrides in tables or references.
2. Header on every page: `Team #<control number>` left; `Page <n>` right. One macro at the top holds the control number. Its current value `00000` is a visible placeholder that **must be replaced** before submission.
3. First page: centered control number, Problem B, year, Summary Sheet, title, concise abstract and keywords. Table of contents begins on the next page.
4. Numbered sections, automatic equation numbers, booktabs tables, source-aware captions, and `thebibliography`/`\cite`. Figures stay within their sections. References use readable clickable source labels, with complete URLs retained in the TeX, instead of printing long URLs across the page. Reference type remains 12-point.
5. One-page decision-maker letter follows the references. The Report on Use of AI begins on a new page after the solution. Neither the letter nor references are silently excluded from the 25-page solution count.
6. No original 2023 HiMCM solution submissions were searched or used.

## Verification status

`python scripts/check_tex_format.py` checks the 12-point declaration, header, Summary Sheet ordering, citation keys, matched environments and existence of included figures/tables. It does **not** establish page count or visual quality. On 18 October 2026, the built-in editor compiler successfully compiled the canonical source after the app-specific Tectonic cache was populated with the official bundle's missing 12-point fonts and packages. The repair script only fetches cache resources; it does not compile a separate PDF. The same editor-generated output is saved as `paper/ebus_transition.pdf`, with source and PDF hashes. It has 25 solution pages and a one-page Report on Use of AI; the summary and letter each fit on one page. Geometry checks found no text outside the expected boundaries. Page overviews and the detailed summary, baseline table, London table, charging results, references and letter were visually inspected. This checks the present draft's layout, not completion of the research. The old ReportLab PDF stays archived because its 9-point text does not meet the chosen contest format.
