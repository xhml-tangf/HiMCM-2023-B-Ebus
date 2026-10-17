# LaTeX format basis and verification boundary

Checked 16 October 2026. This is a 2023 HiMCM **practice** manuscript, not a current contest submission.

## Reference availability

- [COMAP's 2025 HiMCM results](https://www.contest.comap.org/highschool/contests/himcm/2025results.html) identify eight Outstanding teams, including three for Problem B. They list winners, not downloadable full manuscripts. Searches for those teams' complete papers did not locate a verifiable public copy. Therefore this document does **not** claim to reproduce a 2025 winner's exact typography.
- [COMAP's publicly posted 2024 HiMCM examples](https://www.comap.org/images/contests/2024_HiMCM_Examples.pdf) were inspected for visible conventions only: a distinct first-page Summary Sheet, team control number, problem letter, title, page headers and readable numbered sections. The example PDF combines excerpts from several papers, so its typography is not one mandatory template.
- [COMAP's current official instructions](https://www.contest.comap.org/highschool/contests/himcm/instructions.html) provide the hard format rules: English PDF, at least 12-point type; team control number and page number at the top of every solution page; Summary Sheet first; at most 25 pages including contents, references and appendices; no student, advisor or institution names; AI use report after the 25-page solution. Use the competition-year instructions again before any actual submission because rules can change.

## Fixed design decisions in `paper/ebus_transition.tex`

1. `article` class, US Letter, 12-point Latin Modern, 0.80-inch margins. No small-font overrides in tables or references.
2. Header on every page: `Team #<control number>` left; `Page <n>` right. One macro at the top holds the control number. Its current value `00000` is a visible placeholder that **must be replaced** before submission.
3. First page: centered control number, Problem B, year, Summary Sheet, title, concise abstract and keywords. Table of contents begins on the next page.
4. Numbered main sections/subsections, automatic equation numbers, booktabs tables, source-aware captions, and `thebibliography`/`\cite` so added citations do not require manual renumbering.
5. One-page decision-maker letter after references. AI Use Report begins on a new page after the solution. Neither the letter nor references are silently excluded from the 25-page solution count.
6. No original 2023 HiMCM solution submissions were searched or used.

## Verification status

`python scripts/check_tex_format.py` checks 12-point declaration, header, Summary Sheet ordering, citation-key consistency and matched environments. It does **not** establish successful LaTeX compilation or page count. The built-in LaTeX compiler currently returns `Unable to find standard directories for platform` on this Windows host before reporting source diagnostics. The old ReportLab PDF is archived at `paper/archive/legacy_reportlab_preview.pdf` because its 9-point text did not meet the now-fixed contest format. The `.tex` file is the canonical manuscript; no current compliant PDF is claimed until an actual LaTeX engine compiles it and the pages are rendered and inspected.
