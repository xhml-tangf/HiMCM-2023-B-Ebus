# Manuscript review and completion audit

Review date: 18 October 2026. Scope: the complete 25-page PDF, source, code,
figures, data ledger and repository. No original 2023 HiMCM solution paper was
used.

## Requirement check

| Problem task | Evidence in the paper | State |
|---|---|---|
| Q1 ecological model and application | Fall-2023 schedules, battery-range screen, partial-production/operation/maintenance emissions, fuel-mix sensitivity and fixed-route NOx/PM inventory | Class-specific result is 35.3--84.0%; depot construction and end-of-life are explicitly excluded. |
| Q2 financial model with grants up to 50% | Ten-year discounted resource cost, vehicle/infrastructure/O&M/residual components, 0/25/50% agency cases | Class-specific central score is -75.0%; physical garage bids remain absent. |
| Q3 ten-year roadmap in three metropolitan areas | Vancouver, Chicago and London annual purchase/retirement/inventory paths; London integer cohort model | All three end at zero conventional stock in 2033. Route- and garage-specific Chicago/London purchases remain unverified. |
| Q4 one-page decision letter | Page 25 contains recommendations, counts, scores and gates | Present and constrained to one page. |
| Format | 12-point, summary page, contents, 25 solution pages and one AI-report page | Verified by compile and automated layout checks. |

## Substantive corrections completed

- Replaced fictional battery constraints for diesel and trolley vehicles with
  explicit fuel, battery and overhead-supply checks.
- Corrected charging loss attribution by separating battery-delivered energy,
  meter energy and charging efficiency.
- Added source-declared fall-2023 GTFS blocks and calendar exceptions.
- Retained unknown trip distances as monotonic intervals instead of filling
  them with an observed zero.
- Replaced capacity labels with capacity signatures and kept propulsion/trolley
  attribution explicitly provisional.
- Added the distinction between a block request, a physical vehicle and an
  as-operated duty.
- Added fleet-scale interval (1,711--1,733; derived point 1,725) and the
  2025 age/model-year check.
- Replaced the ten-year full-fleet baseline with a 10/17 steady-state renewal
  assumption, with the unknown age roster disclosed.
- Excluded double-deck and trolley costs from the generic depot sub-case; the
  class follow-up adds both vehicle classes and treats 262 trolley renewals as
  a common cost on both comparison paths.
- Corrected the environmental boundary to exclude trolley service in both
  cases and to include renewable-diesel/RNG scenarios.
- Added the 80.6-MW generic and 82.4-MW class charging-scale checks and the
  6--8-year infrastructure lead time.
- Added a 1,419-heavy / 57-deck / 189-shuttle class-specific core envelope
  (CAD 4.712 billion, -75.0%), sizing shared depot capacity from 1,419
  positions and retaining it once.
- Added a 432,768-cell joint assumption audit that exactly reproduces the
  named CAD 4.575-billion / -96.4% cell.
- Quantified fixed-route tailpipe pollution as 126--408 t NOx, 1.11--8.34 t
  PM2.5 and 2.34--14.18 t PM10 per year.
- Added a separate regional value-added/employment layer and kept capital
  activity non-additive to recurring operations.
- Removed the misleading service-plan trend figure and added an annual
  three-city purchase/retirement/stock table with zero conventional endpoints.
- Reduced the manuscript from 26 to 25 solution pages while adding the new
  results.

## Remaining evidence gaps

- 2023 full-year GTFS and an as-operated trip record.
- Block-to-vehicle, depot, pull-out/pull-in and terminal dwell data.
- Exact 2023 vehicle age/propulsion/payload register.
- Site transformer, feeder, charger and available-power limits.
- Winter measurements for the selected 2033 buses.
- Comparable delivered vehicle/site prices for Chicago and London.
- Matched infrastructure, battery-replacement and end-of-life emissions.

These gaps prevent a certified city-wide optimum and full life-cycle score.
They do not prevent the reported fixed-service screening, conditional
cost/emissions scenario or transparent ten-year transfer plan.

## Automated checks

- Python test suite: 41 passed.
- Static LaTeX check: 12-point, 50 references all cited, balanced environments.
- Built-in editor compile: success.
- Same app-owned Tectonic executable exported the PDF.
- PDF QA: 26 total pages, 25 solution pages, page-1 summary, page-25 letter,
  page-26 Report on Use of AI, 45 external source hyperlinks verified, no text-boundary
  or page-limit issues.
