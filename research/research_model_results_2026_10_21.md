# Canonical full-timetable model results (21 October 2026)

The canonical manuscript uses `results/research_model/canonical_v4.json` and
`paper/generated/canonical_macros.tex`. The older inventory and audit figures
remain in the repository but are not alternative answers to the paper question.

## Main result

| Item | Value |
|---|---:|
| Service patterns / calendar days | 25 / 119 |
| Non-trolley calendar trip instances | 2,119,742 |
| Active battery buses | 1,817 |
| Battery fleet with 15% reserve | 2,100 |
| Retained trolleybuses | 275 |
| Firm depot-power requirement | 101.67 MW |
| Annual grid energy | 283.4 GWh |
| Ten-year gross PV, baseline | CAD 5.247 billion |
| Ten-year gross PV, electric plan | CAD 5.804 billion |
| Economic score | −10.63% |
| Full-lifecycle environmental score, converted fleet | +27.53% |
| Full-lifecycle environmental score, whole fleet | +25.51% |
| 2033 operating-emission reduction | +71.93% |
| 2024–2033 transition emissions | 700,360 t CO2e |
| Plan with 50% capital support | CAD 5.301 billion; −4.15% economic score |

The main score is an annualized steady-state comparison over 17-year heavy-vehicle
life, eight-year electric-shuttle life and 30-year facility life. The transition
ledger is a separate near-term accounting result; it is not inserted into the
full-life denominator.

## Sensitivity

| Case | Economic score | Full-life environment | Required power |
|---|---:|---:|---:|
| Retrofit-first, central | −10.63% | +27.53% | 101.67 MW |
| 10% reserve | −12.33% | +29.62% | 101.67 MW |
| Full new build | −18.34% | +9.78% | 101.67 MW |
| Half-power charging | −13.44% | +22.79% | 85.95 MW |
| Severe winter | −14.67% | +16.86% | 122.04 MW |
| Fossil-diesel baseline | −10.63% | +81.90% | 101.67 MW |

## Verification

- 103 regression and canonical-result tests pass.
- Every non-trolley source trip is assigned exactly once.
- Calendar, energy, capacity, SOC, charge-release and first/last-day checks pass.
- The 18-page PDF has 17 solution pages and one AI report page.
- Layout QA reports no page overflow.

The detailed year-by-year ledgers, schedule files, trade-off points and hashes
are under `results/research_model/`. The paper's technical appendix records the
small number of planning assumptions; the main text reports one design decision.
