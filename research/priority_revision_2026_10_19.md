# Priority correction: transition emissions and service claims

Revision date: 19 October 2026. This note records the first correction round
after the independent adversarial review. It closes the emissions time-base
defect and the directly coupled labelling and manufacturing-boundary errors.
It does not claim that the remaining review findings are resolved.

## Implemented correction

`src/transition_ledger.py` now supplies one annual service ledger to both O&M
and emissions. For year $y$, the selected policy share is
$\alpha_y=(y-2023)/10$. Scored conventional kilometres remain
$(1-\alpha_y)D$ until the fleet endpoint. The transition use inventory is

$$\frac{D}{1000}\sum_{y=2024}^{2033}
[(1-\alpha_y)(g+0.0524)+\alpha_y(0.019+0.0675)].$$

The generic scenario, class scenario and 432,768-cell assumption grid all call
this ledger. An independent test enforces the $\alpha_y=0$ and $\alpha_y=1$
endpoints, kilometre conservation, and the audited numerical counterexample.

## Corrected results

| Boundary | Renewable mix | RNG heavy | Weighted mix | Fossil diesel |
|---|---:|---:|---:|---:|
| Generic, reduction (%) | 0.729 | 33.741 | 38.025 | 41.487 |
| Class subset, reduction (%) | 4.563 | 35.613 | 39.558 | 42.730 |

The generic transition inventory is now 373.470--884.084 kt against
376.213--1510.909 kt for renewal. The class subset avoids 17.665--680.056 kt,
against baseline emissions of 387.155--1591.502 kt. These are partial
production, operation and maintenance inventories covering scored conversion
service; they exclude common trolley and retained-BEB activity.

The grid's environmental median and 5th--95th span changed from the invalid
72.6% and 13.3--82.4% to 33.4% and -15.1--41.5%. The generic named case still
reproduces its CAD 4.575-billion and -96.4% economic cell.

Adding one replacement battery to each of the first annual cohort of 162 buses
(335 kWh at 58 kg CO2e/kWh) adds 3.148 kt and changes the renewable-mix score
to -0.108%. This is an illustrative stress, not a predicted replacement year.

## Coupled corrections

- Unknown community-shuttle bodies are now omitted on both comparison sides.
  The previous baseline included 8.373 kt of standard-bus body production for
  shuttle purchases while the electric side used battery-only production.
- The 1,419 heavy positions are a retained proportional inventory scenario.
  They are no longer described as a lower or upper vehicle bound. The 1,647
  purchases and 1,927 endpoint are stock arithmetic, not dispatch certificates.
- The 18 existing BEBs and 1,725 initial stock are unverified scenario
  parameters. The cross-date subtraction 280 minus 262 is not a delivery record.
- Retained inherited integer positions remain unchanged. The earlier implicit
  floor is documented rather than silently changing the headline numbers.
- The paper, figure captions, generated tables, README and older result notes
  now use the corrected ramp and partial-boundary labels.

## Still open from the adversarial review

City-wide duty scheduling, cross-day SOC closure, full terminal-value assets,
commissioning-year feasibility, the Chicago replacement shortfall, and the
APTA roster gap remain open. They are outside this first correction round and
must not be inferred to have passed because the tests and PDF compile.

The current solution PDF has 25 pages plus the separate AI report. The
placeholder control number remains `00000`.
