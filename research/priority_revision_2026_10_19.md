# Priority correction: complete review pass

Revision date: 19 October 2026. This note records the current state after the
independent adversarial review. The complete finding-by-finding matrix is in
`adversarial_review_resolution.md`.

## Numerical result

O&M and GHG share one annual service ledger. Readiness is zero through 2029,
then 25/50/85/100% in 2030--33. The generic partial score is -17.6--15.1%;
the class subset is -14.3--16.2%. The renewable-fuel cases are negative because
vehicle and battery production dominates when conversion is facility-gated.

Generic constant-2023 PV is CAD 4.303 billion versus 2.275 billion (-89.2%).
The class central case is CAD 4.430 versus 2.625 billion (-68.8%); symmetric
0/25/50% grants give -68.8/-38.8/-5.5%. Retained assets and infrastructure
terminal values produce a -41.1 to -106.4% range instead of a single TCO claim.

## Implemented corrections

- A periodic SOC API carries energy and fuel across days and requires cycle
  closure. A zero-charge two-day counterexample now fails.
- A Route 100 terminal-linked sample covers 223 trips with 23 source blocks,
  25 daily fragments and a simultaneous lower bound of 14.
- Distance ceilings are reported at both interval ends: 1,698--1,741 on the
  representative 300-km weekday and at most 1,745 across all 25 patterns.
- Prices are rebased to 2023 CAD with Bank of Canada total CPI; the 3% rate is
  a real-rate scenario.
- Chicago's age bins enter a hard-deadline model. At 185 purchases/year the
  2024 shortfalls are 354, 871 and 901 for 17-, 14- and 12-year caps.
- The 432,768-cell grid fixes annual service kilometres across stock scenarios.
- Common trolley renewal uses symmetric grant eligibility in both paths.
- Strict zero-emission electricity sourcing is labelled UNVERIFIED; operational
  zero-tailpipe and source-contract sensitivities are separate.
- The model equations now show age-zero inventory, integer retirement bounds,
  chargers with `P <= Pmax u`, grid energy and per-vehicle occupancy.

## Remaining external evidence

No full-year 2023 timetable, as-operated vehicle/depot register, firm site power,
road-time matrix, payload test or complete end-of-life inventory exists in the
loaded public evidence. The paper therefore does not claim that its inventory
parameters are a citywide feasible procurement list or complete TCO.
