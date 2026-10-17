# HiMCM 2023 Problem B: electric bus fleet transition

This is a reproducible research workspace and evidence-locked paper draft for
2023 HiMCM Problem B. The original problem PDF is supplied by the user and
remains at its original path. No original HiMCM solution paper was used.

The project separates **verified observations**, **sourced planning
assumptions**, and **illustrative scenarios**. It must never present a 2020
fleet inventory as the actual 2023 fleet or describe hourly service summaries
as a verified vehicle-level schedule.

## Layout

- `data/raw/`: downloaded public primary-source files, with SHA-256 hashes in
  `data/sources.json`.
- `data/processed/`: cleaned 2023 route/time-bin observations and data audit.
- `data/processed/translink_2023_actual_service.csv`,
  `src/audit_service_actual.py`, and `results/actual_service_audit.json`:
  official 2023 actual bus hours, service-km, capacity-km and operating-group
  reconciliation from the 2025 Business Plan, with SeaBus excluded.
- `src/model.py`: trip, passenger capacity, winter traction plus electric
  accessory SOC, home-depot and in-route charger/site, and 2033 fleet
  validation; discounted cost, grant and Pareto primitives.
- `src/run_analysis.py`: observed scale and model-readiness output.
- `src/audit_comparators.py` and `results/comparison_city_audit.json`:
  primary-source Chicago CTA and London TfL 2023 scale checks, kept on their
  own accounting boundaries.
- `data/processed/translink_2020_update_annual.csv`,
  `src/audit_2020_program.py` and `results/2020_program_audit.json`:
  historical 2020 TransLink program awards and nominal cost reconciliation;
  these planned awards are not 2023 deliveries or the target-year solution.
- `data/processed/translink_2026_plan_cohorts.csv`,
  `src/audit_non_electric_lockin.py` and `results/non_electric_lockin_audit.json`:
  later budget revision and named CNG/diesel replacement exposure before 2033;
  overlapping project versions are not added together.
- `data/processed/translink_2025_investment_bus_hours.csv`,
  `src/audit_service_floor.py` and `results/service_floor_audit.json`:
  later planned bus hours screened against the preserved 2023 service floor,
  with the accounting-boundary uncertainty made explicit.
- `src/plot_service_floor.py` regenerates the corresponding manuscript figure
  from the processed source table and audited 2023 actual service total.
- `src/audit_capacity_proxy.py`, `data/processed/vancouver_load_capacity_proxy_2023.csv`
  and `results/capacity_proxy_audit.json`: class-capacity diagnostic from
  official 2023 load-factor cells and 2018 capacity definitions; aggregate
  matches do not identify individual vehicle assignments.
- `tests/`: small but discriminating schedule and cost-transfer tests.
- `results/model_readiness.json`: observed quantities and unresolved gates.
- `src/compute_reference_scores.py` and `results/cpu_reference_scores.json`:
  executable CPU-only, sourced 40-ft diesel/hybrid/CNG renewal reference
  scores, 2024 O&M cross-checks, and sensitivity cases;
  see `research/cpu_reference_score_note.md` for scope and limits.
- `data/processed/translink_2025_plan_cohorts.csv`,
  `data/processed/translink_2020_depot_ratios.csv`,
  `src/audit_capital_cohorts.py`, and `results/capital_cohort_audit.json`:
  auditable *retrospective planned* retirement and replacement cohorts, project
  budgets, and a historical depot/winter-heat stress test; no claim of delivered
  buses, current technical specifications or trip adequacy.
- `paper/ebus_transition.tex`: canonical 12-point HiMCM-style LaTeX research
  draft. Set the official team control number at the top before submission.
- `paper/archive/legacy_reportlab_preview.pdf`: old, non-compliant 9-point
  preview retained only for provenance; **do not submit or use for format QA**.
- `research/format_basis.md`: official format rules, exemplar availability,
  fixed style choices and compiler status.
- `research/`: parameter/source ledger and independent literature notes.

To reproduce the current evidence audit, run `python scripts/fetch_sources.py`
with network access to obtain the official raw sources, then
`python src/audit_data.py`, `python src/audit_service_actual.py`,
`python src/run_analysis.py`, `python src/audit_comparators.py`,
`python src/audit_2020_program.py`,
`python src/audit_non_electric_lockin.py`,
`python src/audit_service_floor.py`,
`python src/audit_capacity_proxy.py`,
`python src/plot_service_floor.py`,
`python src/compute_reference_scores.py`, `python src/audit_capital_cohorts.py`,
and `python -m pytest tests -q`. Source URLs and SHA-256 hashes are in
`data/sources.json`. Raw source PDFs/CSVs are kept out of the Git repository;
the retrieval script reconstructs them, subject to source availability. Run
`python scripts/check_tex_format.py` for static manuscript checks. The
current built-in LaTeX compiler cannot download its uncached Tectonic bundle,
so no newly compiled PDF is claimed. Compile `paper/ebus_transition.tex` with a working
LaTeX engine and inspect every page before submission.

## Boundary

Main case: TransLink fixed-route bus service in Metro Vancouver, including
community shuttles and trolleybuses. HandyDART, SeaBus, and rail are excluded.
Chicago CTA and London TfL are comparison cases. The 2024-2033 deadline is a
counterfactual target; TransLink's own target is 2040.

## Result status

2023 public route data account for 98.035% of independently reported actual
fixed-route bus service hours. The official 2023 actual bus totals are
5,575,772 hours, 106,868,324 service-km and 5,715,791,401 capacity-km.
The ratio of capacity-km to service-km is 53.48 passenger spaces per bus-km.
Official historical vehicle-capacity definitions explain 96.56% of positive
2023 aggregate load cells through six clear capacity clusters, but not
individual trip vehicle assignments. The official 2023 revenue-fleet
operating-GHG total is 112,591 tonnes CO2e across all modes; it is not a
bus-only or life-cycle value. June 2023 agency slides add BEB, charger and
depot screening prices, with planning rather than awarded-project status.
Official reports give 280 trolley/BEB buses combined in December 2023 and
299 CNG buses, while a same-day official article describes the electric split
as about 275 trolleys and five BEBs. A February notice says 262 trolleys,
so the exact December electric split is unresolved. Later budgets reveal
partial retirement cohorts. Exact
vehicle blocks, depot electrical limits and a complete 2023 class/age/depot
register remain unresolved. The city-wide schedule, scores, Pareto frontier
and numeric purchase table are therefore `UNVERIFIED`/null in
`results/model_readiness.json`. The 2019-CAD 40-ft comparisons and 2025
capital-program audit are explicitly conditional/retrospective. Entering
real trip and site data into `check_schedule` is required before any full-city
solution can be called service-feasible.
