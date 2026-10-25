# Adversarial review resolution matrix

Historical first-round record. The V2 terminal-value and periodic-validation corrections supersede the relevant closure claims below; see `materials/research/review_v2_resolution.md`.


Audit date: 19 October 2026. Source review:
`D:/AI/ebus-peer-review/审稿报告.md`. This file maps every F finding to the
current code result, manuscript claim and verification evidence. It does not
turn unavailable city records into facts.

| Finding | Resolution | Authoritative evidence |
|---|---|---|
| F01 emissions time base | O&M and GHG use one annual service ledger. Site readiness is zero through 2029, then 25/50/85/100% in 2030--33. Battery replacement is a stress case. | `src/transition_ledger.py`; `tests/test_transition_ledger.py`; generic and class environment JSON; paper Tables 3--4 |
| F02 task ratio to vehicles | No dispatch interpretation remains. A small Route 100 terminal-linked plan has 223 trips, 23 source blocks and 25 daily fragments, with a simultaneous-trip lower bound of 14. The city numbers are inventory scenarios. | `results/vancouver_block_range_audit.json`; `data/processed/route100_terminal_duty_plan_2023.csv`; `tests/test_small_duty_plan.py` |
| F03 18 delivered / 1725 stock | Labels are unverified scenario parameters. Cross-date subtraction is explicitly not a delivery record; no verified stock bound is claimed. | GTFS/fleet note; paper assumptions A4; fleet audit JSON |
| F04 manufacturing asymmetry | Unknown shuttle bodies are omitted on both sides. A per-year, per-class production ledger is reported. Common trolley and retained BEBs are excluded from the environmental percentage denominator, and the scope is stated. | `results/vancouver_full_fleet_bound.json:production_ledger`; `manufacturing_boundary`; paper Table 5 scope |
| F05 cross-day SOC | `check_periodic_schedule` carries energy/fuel state across days and requires cycle closure. The 60-km/day, zero-charge counterexample passes once but fails a repeating cycle. | `src/model.py`; `tests/test_model.py`; paper equations (5)--(7) |
| F06 terminal assets | A symmetric 17-year asset memo covers retained initial stock, purchases and sale receipts. Infrastructure lives are separate. Score ranges replace the purchase-only headline. | `src/asset_boundary.py`; `src/build_asset_boundary.py`; `results/vancouver_asset_boundary.json`; paper Table 6 |
| F07 year readiness and Chicago age | Vancouver credits no conversion before 2030. Chicago uses reported age bins and oldest-age deadlines; 2024 shortfalls are 354/871/901 for 17/14/12-year caps. | `results/three_city_roadmap.json`; `paper/tables/chicago_age_roadmap.tex`; `tests/test_three_city_inventory.py` |
| F08 sensitivity service control | The 432,768-cell grid holds annual scored kilometres fixed across stock scenarios. Fleet changes affect capital and positions only. | `src/propagate_transition_uncertainty.py`; `service_km_control`; `tests/test_transition_uncertainty.py` |
| F09 ceiling direction | Both lower- and upper-distance ceiling counts are reported. Representative 300-km requests are 1,698--1,741; all-pattern upper maximum is 1,745. | `src/analyze_vancouver_blocks.py`; block audit JSON; Table 2 |
| F10 common-trolley grant | Comparator and plan receive the same common-trolley grant percentage. The prior one-sided scenario is only a named asymmetric counterfactual. | `src/build_full_fleet_bound.py`; `grant_cases_symmetric_common_trolley`; paper Table 5 |
| F11 zero-emission source | Operational endpoint is zero-tailpipe electric propulsion/accessories. Strict source certification is `UNVERIFIED`; average-grid and zero-source contract sensitivities are separate. | `results/vancouver_full_fleet_bound.json:electricity_source_sensitivity`; `endpoint_definition`; paper boundary section |
| F12 master-model closure | Age-zero stocks and integer domains, power/occupancy, grid energy and cross-day closure are explicit. The city master problem is labelled conceptual; only bounded submodels are claimed solved. | `src/model.py`; paper equations (1)--(10); periodic tests |
| F13 local numerical labels | Maximum trip day is 22,494; maximum-block day is separately 8 September. Range table uses paired 149/150, 184/185, 250/251 and 300/300 labels. | `results/vancouver_gtfs_baseline_audit.json`; `results/vancouver_block_range_audit.json`; Tables 1--2 |

## Formula and claim checks

- (1) now has an age-zero purchase term and integer retirement bounds.
- (2)--(3) retain every recovered trip and capacity proxy. The ill-defined
  simultaneous-capacity equation was removed from the hard constraints.
- (5) reports both distance endpoints and no vehicle-bound claim.
- (6)--(8) link grid energy, vehicle power, charger occupancy and day-to-day
  state. A return charge can restore the cycle; autonomous state reset cannot.
- (10) is explicitly a conceptual master problem. No city Pareto frontier is
  reported.
- (11) now uses constant 2023 CAD and an asset terminal-value ledger.
- (13)--(15) are reported as a partial production/operation/maintenance score,
  not a complete life-cycle inventory. Common trolley and retained BEB terms
  are outside the denominator.
- (17) uses nonnegative integer variables. The London proof remains restricted
  to its common-release cohort model.

## Remaining evidence limits

There is still no full-year 2023 timetable, as-operated vehicle/depot register,
per-site firm power, charger commissioning record, road-time matrix, payload
test, or complete end-of-life boundary. The paper therefore does not claim a
citywide feasible procurement list. F02, F07 and F11 are resolved by a smaller
audited model plus an explicit non-certification boundary, which is the review's
stated fallback where public records cannot support the stronger claim.

## Reproduction

Run `python scripts/reproduce_local.py`, then
`python scripts/check_tex_format.py`,
`python scripts/check_manuscript_numbers.py`, compile the TeX through the
built-in editor, and run `python scripts/qa_editor_pdf.py`.
