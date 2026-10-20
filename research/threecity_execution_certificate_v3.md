# Three-city execution certificate, version 3

Date: 2026-10-20. Scope: Chicago and London only. This note supplements the
existing three-city model without changing its result files.

## Result

The new certificate separates two claims that the prior roadmap combined:

1. **Fleet-class body compatibility and stock conservation** can be proven
   from the CTA and TfL public data after explicit life and replacement rules.
2. **Route-level service preservation and charging feasibility** still cannot
   be proven from these data. Neither city audit contains vehicle-to-block,
   route-to-garage, charger, firm-power or winter-energy records.

The machine-readable result is
`results/threecity_execution_certificates_v3.json`; procurement batches are in
`data/processed/threecity_execution_batches_v3.csv`, and the reproducible
builder is `src/build_threecity_execution_v3.py`.

## Chicago: current official plan is insufficient for a 2033 electric endpoint

CTA's FY2024 Proposed Budget describes a 2023 year-end inventory of 1,875
buses: 1,576 standard and 299 articulated. It also identifies 25 current
40-foot BEBs: two from 2014 and 23 from 2022. The Bus Fleet Management Plan
prints the following maximum purchase envelope (PDF page 63):

| body | 2023--26 | 2027--33 | total |
|---|---:|---:|---:|
| 40-foot standard | 457 | 700 | 1,157 |
| 60-foot articulated | 140 | 170 | 310 |
| total | 597 | 870 | 1,467 |

The strict 2033 endpoint requires every one of the 1,850 non-electric slots to
be replaced by an electric bus. The two known 2014 BEBs also reach a 14-year
age before 2033 and need renewal; the 23 2022 BEBs remain inside the horizon.
Thus a lower-bound purchase need is 1,852 buses, not 1,467:

| item | standard 40-foot | articulated 60-foot | total |
|---|---:|---:|---:|
| current stock | 1,576 | 299 | 1,875 |
| current BEBs | 25 | 0 | 25 |
| non-electric slots to replace | 1,551 | 299 | 1,850 |
| known 2014 BEB renewals | 2 | 0 | 2 |
| minimum purchases | 1,553 | 299 | 1,852 |
| official FMP envelope | 1,157 | 310 | 1,467 |
| shortfall / (surplus) | 396 | (11) | **385** |

This is deliberately generous to the existing plan: all 1,467 purchases are
counted as future, although some 2023 purchases are already inside the
year-end inventory. The statement is a certificate against the **published
FMP envelope**, not a proof that CTA physically cannot buy more buses.

The CTA budget also says 200 additional buses are scheduled for delivery in
2024 and 430 1000-series buses receive a life-extending overhaul for service
through 2028/29 (PDF pp. 32 and 66). Using the public age bins with their
oldest possible member, CTA's 14-year useful-life criterion creates 1,056
definitely-due slots in 2024. Moving all 430 funded extensions to 2029 leaves
626 due in 2024:

| 2024 ramp case | due |
|---|---:|
| no extension | 1,056 |
| 430 funded 1000-series extensions | 626 |
| 608 maximum FMP life-extending overhauls | 448 |
| budgeted new-bus deliveries in 2024 | 200 |
| gap after 430 extensions | **426** |
| gap after 608 extensions | **248** |

The entire 2023--26 purchase envelope is only 597 buses. Even if every one of
those buses were delivered in 2024 and all were electric, it would still be
29 buses below the 626-slot post-extension deadline. Since some of the 597
were already delivered in 2023, the actual gap is larger. Overhauls keep a bus
in service; they do not replace its diesel drivetrain and therefore cannot
close the 2033 electric-stock deficit.

### Chicago schedules produced

The model solves integer minimum-peak schedules with body-type conservation:

| life cap | 2024 due | minimum peak annual purchases |
|---|---:|---:|
| 12 years | 1,086 | 1,086 |
| 14 years (CTA plan) | 1,056 | 1,056 |
| 17 years | 539 | 539 |
| 14 years + 430 funded extensions | 626 | 626 |
| 14 years + 608 maximum extensions | 448 | 448 |

Each schedule purchases 1,551 standard and 299 articulated non-electric
replacements, adds the two known 2014 BEB renewals at the applicable deadline,
and ends with zero non-electric slots. The JSON retains annual standard,
articulated and BEB-renewal quantities. The schedule's peak is an accounting
capacity requirement, not a factory, garage or bid certificate.

## London: body-compatible renewal plan is executable at fleet-class level

The TfL audit has 8,643 slots: 2,445 single-deck and 6,198 double-deck. It
records 950 electric buses and 20 hydrogen double-deckers. Under the strict
electric endpoint, hydrogen counts outside the electric stock, so there are
2,083 non-electric single-deck slots and 5,610 non-electric double-deck slots
to convert. Current audited electric stock is 362 single-deck and 588
double-deck; these are not counted as spare replacements.

The MILP is rerun from the original registration/body/propulsion table. Every
non-electric cohort is converted before its selected chassis-life deadline;
existing electric cohorts are renewed only if they reach the cap before 2033;
single-deck and double-deck counts are conserved separately. Results:

| life cap | 2024 conversions | minimum peak | total deliveries | EV renewals |
|---|---:|---:|---:|---:|
| 12 years | 2,568 | 2,568 | 8,428 | 735 |
| 14 years | 977 | 977 | 7,940 | 247 |
| 17 years | 775 | 776 | 7,759 | 66 |

All three runs report solver status `OPTIMAL`, zero MIP gap in all phases, and
peaks equal to the independent cumulative-deadline bound. The 17-year plan
converts 7,693 non-electric slots and renews 66 existing electric slots. Its
maximum single-year body batch is 408 single-deck and 776 double-deck; the
annual CSV records every year and registration-vintage batch.

This is an **executable fleet-class order schedule** in the narrow sense that
every audited body-type slot has an electric successor and the annual total
does not exceed the selected cap. It is not a route or garage schedule: TfL's
local route blocks, depot power, charger occupancy, manufacturing lead times
and local prices are absent. The 17-year life cap is a scenario, not a quoted
TfL retirement rule.

## Residual evidence gaps

- Chicago age data are six coarse bins, not vehicle IDs. The 430 and 608
  extension cases defer the oldest compatible standard buses; the source does
  not identify exactly which 1000-series units receive funded overhauls.
- CTA's 200 deliveries are an annual budget statement, not a type-specific or
  contractually guaranteed delivery date.
- London's audit supplies stock cohorts, not route assignments or depot power.
- Neither model includes infrastructure, prices, winter heating, spare-fleet
  growth or vehicle performance under load.

## Reproduction

```powershell
python src/build_threecity_execution_v3.py
python -m pytest -q tests/test_threecity_execution_v3.py
```

The added six tests check the official-plan deficit, the 2024 ramp, integer
deadline compliance, body conservation, all-electric endpoints, zero solver
gaps, analytic peaks and procurement CSV conservation.
