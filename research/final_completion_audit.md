# Final completion audit

Audit date: 18 October 2026. This file is the requirement-by-requirement
delivery check for the 2023 HiMCM B project. It records current evidence and
the remaining external-data boundaries; it does not replace the paper.

| Requirement | Current evidence | Status |
|---|---|---|
| Q1: environmental model and application | Fall-2023 GTFS audit; class/duty range screens; 432,768-case assumption grid; partial-production/operation/maintenance GHG inventory; separate NOx/PM inventory | Answered with named boundaries |
| Q2: financial model and matching grants | Ten-year inventory, capital/O&M/residual envelope, 0/25/50% agency cases, price-mixed label, O&M-rate sensitivity | Answered as a screening appraisal; no awarded garage bids |
| Q3: ten-year roadmaps in three metros | Annual purchase/retirement/EV-stock/conventional-stock table; Vancouver class model, Chicago linear stock path, London solved 17-year cohort model; all end at zero conventional stock | Answered as stock-flow plans |
| Q4: one-page decision letter | PDF page 25; fits on one page; carries class-specific counts, cost/environment results and gates | Complete |
| Complete PDF and source | `paper/ebus_transition.pdf`, `paper/ebus_transition.tex`; 25 solution pages plus one Report on Use of AI | Compiles and passes layout checks |
| Reproducibility | `scripts/reproduce_local.py` builds source audits, models, figures, tables and tests | Passes; 41 tests |
| Documentation | `README.md`, parameter ledger, model notes, source/provenance JSON, AI query log | Present |
| High-level review | `research/manuscript_review.md`, `research/outstanding_format_findings.md`, independent final paper/model audits | Corrections applied |

## Numerical checks

- 2023 fixed-route bus total: 5,575,772 hours, 106,868,324 km and
  5,715,791,401 capacity-km after SeaBus exclusion.
- Fall GTFS: 54,497 trips, 25 service patterns, 1,752 representative weekday
  blocks and 20,679 consecutive transfers.
- Generic non-deck case: 1,612 net BEB positions; CAD 4.575 billion versus
  CAD 2.329 billion; -96.4%; 29.2--82.4% partial emissions reduction.
- Class-specific case: 1,647 route BEB purchases plus 262 common trolley
  renewals, 1,445 conventional retirements, 1,927 electric assets and zero
  conventional assets in 2033. Central price-mixed PV is CAD 4.712 billion
  versus CAD 2.692 billion (-75.0%);
  25/50% grant scores are -42.8/-10.5%; partial-production emissions
  reduction is 35.3--84.0%.
- The 1,419-position shared depot is CAD 2.087 billion, not the generic
  1,612-position CAD 2.371-billion depot allocation.
- Assumption grid: 432,768 distinct cells; the named cell reproduces gross PV,
  economic score and environment score with zero difference.

## Verification commands

```powershell
python scripts/reproduce_local.py
python scripts/check_tex_format.py
python scripts/qa_editor_pdf.py
python scripts/record_pdf_build.py
python -m pytest -q
git diff --check
```

Expected current state: 41 tests pass; static format passes; PDF QA has 26
pages total, 25 solution pages, summary page 1, letter page 25 and AI report
page 26; all 45 external links are present.

## Remaining external boundaries

- The formal team control number has not been supplied; `00000` remains a
  deliberate placeholder. It must be replaced before contest submission.
- A 2023 full-year/as-operated timetable, block-to-vehicle/garage mapping,
  firm site power and an audited 2023 class-age-depot roster are not public.
- APTA's 2023 vehicle ZIP is blocked by a Cloudflare challenge; no row was
  invented. See `research/apta_2023_fleet_note.md`.
- Class-specific shuttle and double-deck glider-production inventories remain
  partial; the paper labels the environmental result accordingly.
- A remote Git upload is complete only when a remote ref is verified. Local
  history is the fallback specified by the project brief.
