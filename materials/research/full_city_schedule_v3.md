# Vancouver full-city absolute-time schedule screen v3

Date: 2026-10-20. Input: the pinned fall-2023 TransLink GTFS manifest and its
25 unique service-ID patterns. Outputs:

- `results/vancouver_full_city_schedule_v3.json`
- `results/vancouver_full_city_schedule_v3.csv`
- `src/build_full_city_schedule_v3.py`
- `tests/test_full_city_schedule_v3.py`

## What was executed

The source feed has 54,497 unique bus-trip records and its pinned calendar
contains 119 service days. Executing one representative date for each of the 25
unique service-ID patterns yields 495,198 trip instances and covers every one
of those 119 days through its service-ID pattern. The calendar-weight is
2,410,442 scheduled trip occurrences. Every trip in every screened pattern is
retained. The code uses the
published start and end seconds directly. It does not modulo, clip, drop or
shift trips after midnight.

For each pattern, the screen reports:

1. half-open trip overlap and exact-class interval concurrency;
2. consecutive-trip gaps within each original GTFS block;
3. a necessary transfer screen using five minutes plus straight-line distance at
   50 km/h;
4. source-block task fragments under a 300-km range screen, with and without
   the uniform transfer screen;
5. a traction-only winter energy lower bound using published class proxy rates;
6. comparison with the declared 2033 scenario inventory of 1,419 heavy,
   57 double-deck, 189 shuttle and 262 trolley positions.

## Numerical findings

- Maximum concurrent trips in any screened pattern: **1,089**.
- Maximum exact-group concurrency: **811 heavy**, **107 shuttle**, **37 deck**,
  and **147 trolley**. These counts fall below the declared scenario inventory,
  so vehicle count alone does not reject the 1,927-position endpoint. This is a
  count screen, not a vehicle-to-trip assignment.
- Maximum source-block transfer failures under the declared five-minute and
  50-km/h policy: **4,621** on 2023-09-08; the 2023-10-13 maximum-trip pattern
  has **4,606**. These are policy-screen failures, not observed service failures.
- The 2023-10-13 pattern has **265** blocks whose upper-bound distance exceeds
  300 km; the maximum is **745.3279 km**.
- At 300 km, range-only splitting produces **2,032 task fragments**. Applying
  both the range and uniform-transfer screens produces **6,501** fragments on
  2023-09-08. A fragment is a task segment, not a physical vehicle lower bound:
  later work could reuse a bus after a verified charge or exchange.
- The 2023-10-13 traction-only winter lower bound is **469.208 MWh/day** at the
  battery. At 90% charging efficiency it is **521.342 MWh/day** at the grid. An
  eight-hour site-wide average would require **65.168 MW**. Accessory heating is
  excluded; trolleys are treated as overhead traction with feeder capacity
  unverified.
- Published times extend to **29.983 h** (2023-12-29). A midnight reset would be
  categorically wrong.

## Status and boundary

Overall status is **UNVERIFIED**, with a separate
**FAIL_UNDER_DECLARED_5MIN_50KMH_POLICY** result for original block chains. The
following inputs are still absent:

- vehicle-to-block and block-to-garage assignments;
- depot and terminal parking, charger slots, charger power and grid limits;
- utility interconnection and commissioning dates;
- measured winter payload and accessory heating load;
- terminal dwell/geometry and trolley feeder capacity.

Therefore the screen proves that all source trips are represented and that
exact-class concurrency is below the scenario inventory. It cannot prove that a
specific fleet can execute all work while charging. The high transfer-failure
count also means the original block IDs cannot be treated as certified duties.

## Paper-safe wording

> Across all 25 unique fall-2023 service patterns, we retain every published
> trip. Exact-class concurrency is at most 811 heavy, 107 shuttle, 37 double-deck
> and 147 trolley positions, below the conditional 2033 inventory. This is a
> vehicle-count lower bound only. Under a uniform five-minute turn and 50-km/h
> straight-line connection screen, 4,621 of 20,736 transitions on the
> maximum-block day fail. At 300 km, 265 blocks require a recharge or exchange,
> and the traction-only winter electricity is 469 MWh/day. The citywide
> schedule remains UNVERIFIED until vehicle, garage, charger, firm-power and
> winter-load records are supplied.

## How to upgrade the status

Supply the missing records and rerun the exact `check_periodic_schedule` API on
materialized vehicle assignments. A PASS must retain every trip, satisfy the
declared transfer policy, all class/capacity and payload constraints, SOC and
charger/site limits, and cycle closure. The current screen deliberately stops
before imputing any of those inputs.
