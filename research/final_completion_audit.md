# Final completion audit

Audit date: 19 October 2026. Current sign-off after the adversarial review.

| Requirement | Current evidence | Status |
|---|---|---|
| Environmental model | One service ledger; readiness, production, operation, maintenance; negative cases retained | Implemented |
| Financial model and grants | Constant 2023 CAD; gross and symmetric grant cases; asset/infrastructure range | Implemented |
| Three metropolitan roadmaps | Vancouver facility-gated inventory, Chicago age-deadline stress, London solved cohort schedule | Implemented with stated boundaries |
| Decision letter | One page in the 25-page solution | Verified |
| Full PDF | 25 solution pages plus one AI report | Verified |
| Reproduction | `python scripts/reproduce_local.py`; all tests and manuscript checks | Verified |
| Review closure | F01--F13 and equation checks mapped in `adversarial_review_resolution.md` | Complete for public evidence |

## Numerical checks

- Generic central PV: CAD 4.303 billion vs 2.275 billion; -89.2%; ranks
  -49.5/-9.8% under symmetric 25/50% grants.
- Class central PV: CAD 4.430 billion vs 2.625 billion; -68.8%; symmetric
  25/50% grant scores -38.8/-5.5%; high vehicle case CAD 4.726 billion.
- Asset/infrastructure score range: -41.1 to -106.4%.
- Generic environmental range: -17.6 to 15.1%; class: -14.3 to 16.2%.
- Representative 300-km requests: 1,698--1,741; all-pattern upper maximum 1,745.
- Route 100: 223 trips, 23 blocks, 25 daily fragments, lower bound 14.
- Sensitivity grid: 432,768 cells with fixed annual service-km; economic
  5th/median/95th -140.2/-114.0/-83.4%, environment -33.7/7.8/15.2%.
- Chicago 2024 hard-deadline shortfalls: 354/871/901 for 17/14/12-year caps.
- London 17/14/12-year peaks: 776/977/2,568 original slots per year.

## Verification commands

- `python -m pytest -q`
- `python scripts/check_tex_format.py`
- `python scripts/check_manuscript_numbers.py`
- `python scripts/qa_editor_pdf.py`
- `python scripts/reproduce_local.py`

## Limits

No full-year 2023 GTFS, as-operated fleet/depot record, per-site firm power,
road-time matrix, winter payload test or complete end-of-life inventory was
available. The manuscript labels the city inventory conditional and the strict
zero-emission electricity source `UNVERIFIED`; it does not claim citywide
service certification or a complete total cost of ownership.
