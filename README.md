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
- `src/model.py`: trip, passenger capacity, winter SOC, charger/site and
  2033 fleet validation; discounted cost, grant and Pareto primitives.
- `src/run_analysis.py`: observed scale and model-readiness output.
- `tests/`: small but discriminating schedule and cost-transfer tests.
- `results/model_readiness.json`: observed quantities and unresolved gates.
- `src/compute_reference_scores.py` and `results/cpu_reference_scores.json`:
  executable CPU-only, sourced 40-ft diesel/hybrid/CNG renewal reference
  scores, 2024 O&M cross-checks, and sensitivity cases;
  see `research/cpu_reference_score_note.md` for scope and limits.
- `data/processed/translink_2025_plan_cohorts.csv`,
  `src/audit_capital_cohorts.py`, and `results/capital_cohort_audit.json`:
  auditable *retrospective planned* retirement and replacement cohorts, project
  budgets, and replacement ratios; no claim of delivered buses or trip adequacy.
- `paper/ebus_transition.tex`: canonical 12-point HiMCM-style LaTeX research
  draft. Set the official team control number at the top before submission.
- `paper/archive/legacy_reportlab_preview.pdf`: old, non-compliant 9-point
  preview retained only for provenance; **do not submit or use for format QA**.
- `research/format_basis.md`: official format rules, exemplar availability,
  fixed style choices and compiler status.
- `research/`: parameter/source ledger and independent literature notes.

To reproduce the current evidence audit, run `python scripts/fetch_sources.py`
with network access to obtain the official raw sources, then
`python src/audit_data.py`, `python src/run_analysis.py`,
`python src/compute_reference_scores.py`, `python src/audit_capital_cohorts.py`,
and `python -m pytest tests -q`. Source URLs and SHA-256 hashes are in
`data/sources.json`. Raw source PDFs/CSVs are kept out of the Git repository;
the retrieval script reconstructs them, subject to source availability. Run
`python scripts/check_tex_format.py` for static manuscript checks. The
current local LaTeX compiler is unavailable on this host, so no newly
compiled PDF is claimed. Compile `paper/ebus_transition.tex` with a working
LaTeX engine and inspect every page before submission.

## Boundary

Main case: TransLink fixed-route bus service in Metro Vancouver, including
community shuttles and trolleybuses. HandyDART, SeaBus, and rail are excluded.
Chicago CTA and London TfL are comparison cases. The 2024-2033 deadline is a
counterfactual target; TransLink's own target is 2040.

## Result status

2023 public route data account for 98.013% of statutory bus service hours.
Official reports give 280 trolley/BEB buses combined in December 2023 and
299 CNG buses, while later budgets reveal partial retirement cohorts. Exact
vehicle blocks, depot electrical limits and a complete 2023 class/age/depot
register remain unresolved. The city-wide schedule, scores, Pareto frontier
and numeric purchase table are therefore `UNVERIFIED`/null in
`results/model_readiness.json`. The 2019-CAD 40-ft comparisons and 2025
capital-program audit are explicitly conditional/retrospective. Entering
real trip and site data into `check_schedule` is required before any full-city
solution can be called service-feasible.
