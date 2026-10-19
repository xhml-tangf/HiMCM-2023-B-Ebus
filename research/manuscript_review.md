# Manuscript review and completion audit

Review date: 19 October 2026. Current status is detailed in
`adversarial_review_resolution.md`; this file records the submission-facing
checks only.

| Requirement | Evidence | State |
|---|---|---|
| Environmental application | Facility-gated service ledger, production/operation/maintenance boundary, negative cases retained | Answered with named partial boundary |
| Financial application and grants | Constant 2023 CAD, symmetric 0/25/50% grants, asset and infrastructure terminal-value range | Answered as a conditional appraisal |
| Three-city ten-year roadmaps | Vancouver facility-gated inventory, Chicago age-deadline stress, London solved cohorts | Answered; local dispatch remains a gate |
| Decision letter | PDF page 25 | One page |
| Format | 25 solution pages plus one AI report | Verified |
| Reproducibility | Full local pipeline and 63 tests | Verified |

## Numerical checks

- Generic central PV: CAD 4.303 vs 2.275 billion, -89.2%; symmetric grant
  scores -49.5/-9.8%.
- Class central PV: CAD 4.430 vs 2.625 billion, -68.8%; symmetric grant
  scores -38.8/-5.5%.
- Asset/infrastructure range: -41.1 to -106.4%.
- Generic partial environment: -17.6 to 15.1%; class: -14.3 to 16.2%.
- Route 100: 223 trips, 23 blocks, 25 daily fragments, lower bound 14.
- Chicago 2024 hard-age shortfalls: 354 (17y), 871 (14y), 901 (12y).
- London peaks: 776, 977 and 2,568 original slots/year.

Visual layout, source links and the AI page are checked by
`python scripts/qa_editor_pdf.py`. The city inventory does not certify a
citywide feasible procurement list.
