# Remaining-evidence closure, 20 October 2026

This note records the evidence obtained after the second adversarial review
and the limits that remain. The machine-readable outputs, not this narrative,
are authoritative.

## Fleet and depot facts now measured

- The 14 December 2023 agency release reports 280 trolley-electric and
  battery-electric assets. The same-day operator blog gives the closest public
  split, approximately 275 trolleys and five BEBs. The model therefore uses
  275/5 as its central split and retains 262/18 only as a stress case.
- The 2020 fleet plan lists six operating centres with 1,991 nominal 40-foot
  equivalent spaces and Marpole planned for 300. The June 2023 operator
  package says current depots are full and estimates about 2,000 more spaces
  by 2035; recent depot delivery takes more than six years.
- The 2024 transition plan reports 78 MW of additional system load by 2040.
  BC Hydro can serve centres transitioning before 2035 and on-route chargers
  required before 2030, but new feeders are required after 2035, at new
  centres and for seven on-route locations. Existing-centre charging takes
  6--8 years.
- Nova LFSe+ evidence gives up to 564 kWh, 450-kW overhead or 150-kW plug
  charging, and 68 versus 59 passengers in four- versus six-battery
  configurations. TransLink's winter prototype exceeded 150 km per charge.
  These are product/prototype facts, not a citywide payload or winter test.

## Full-city absolute-time screen

`src/build_full_city_schedule_v3.py` executes one representative date for
each of the feed's 25 service patterns, covering all 119 calendar days and
495,198 trip instances while preserving every trip. Published end times reach
29.983 hours. Exact-class peak concurrency is 811 heavy, 107 shuttle, 37
double-deck and 147 trolley positions, below the conditional 2033 stock.

This is a necessary count screen. The worst original-block day has 4,621 of
20,736 connections failing the declared five-minute plus 50-km/h screen; 265
blocks exceed 300 km. Traction-only winter energy is 469.208 MWh/day at the
battery, 521.342 MWh/day grid-side, or 65.168 MW averaged over eight hours
before accessories. Overall status remains `UNVERIFIED`; source blocks are
not certified duties.

## Cost and environmental bridges

The 2020 fleet plan gives the missing annualized 2019-CAD lifecycle rates for
battery replacement, charger maintenance and extra operator labour. Applying
only those absent components once to electric service-km adds CAD 26.3--89.8
million PV and changes the class score from -67.7% to -68.7%-- -71.1%.

The environment bridge adds plan-only charging-equipment lifecycle and depot
embodied carbon. Charging equipment contributes 4.269--8.539 t CO2e per unit
in the transfer case. Marpole's published 800,000 ft2 floor area, 340-bus
capacity and a 650 kgCO2e/m2 scenario give 201.6 kt for the scaled heavy
facility, plus 6.5--13.0 kt for chargers. Including these gives class scores
of -67.0% to -68.6% for renewable renewal, -9.7% to -10.3% for RNG-heavy,
-2.4% to -2.9% for the weighted mix, and 3.0% to 3.4% for fossil diesel.

## Chicago and London execution certificates

- Chicago's published FY2024 FMP envelope contains 1,467 purchases through
  2033. Strict replacement of 1,850 non-electric slots plus two old BEB
  renewals needs 1,852: a 385-bus shortfall. After 430 funded life extensions,
  626 buses are due in 2024 versus 200 budgeted deliveries, a 426-bus ramp gap;
  even 608 extensions leave a 248-bus gap. This refutes the current published
  envelope, not the possibility of another order.
- London has a body-compatible MILP plan. At a 17-year cap it converts 7,693
  non-electric slots, renews 66 existing electric slots and peaks at 776. The
  14- and 12-year peaks are 977 and 2,568. Every phase is `OPTIMAL` with zero
  gap and single/double-deck conservation. Route, depot and charging
  compatibility remain outside that certificate.

## Publicly unavailable data

The following remain unavailable despite direct official-source searches:

- a dated vehicle-level 2023 class/age/depot/status register;
- vehicle-to-block and block-to-garage assignments;
- actual depot occupancy and class-compatible parking;
- site transformers, feeder segments, firm MW and interconnection costs;
- route-level winter kWh/km, heater load and loaded-axle approval;
- trolley feeder concurrency and route paths;
- full-year as-operated times and passenger loads.

TransLink's FOI log records several relevant 2023 records as released to an
applicant, but the public request page contains no attachments or URIs. The
official APTA 2023 vehicle archive endpoint returned HTTP 403. No private
record is inferred from those facts. The itemized audit is
`research/data/processed/unresolved_evidence_registry.csv`; it separates
public gaps from quantities outside the 2033 accounting horizon.

## Verification

`python scripts/reproduce_local.py` rebuilds the analyses, including the
full-city screen, bridges and three-city certificates. The current suite has
88 passing tests. The paper remains within 25 solution pages plus its AI-use
report when the final render is checked.
