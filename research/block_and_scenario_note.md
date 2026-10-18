# Fall-2023 blocks and conditional 2024--2033 scenario

## Source and semantics

The public mirror preserves TransLink GTFS 23SEP_20231020 at commit
eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b. Each downloaded file matches its
Git blob SHA-1 and has a SHA-256 in
data/processed/vancouver_gtfs_2023_provenance.json. The feed covers
2023-09-04 through 2023-12-31, not all of 2023 and not actual execution.

GTFS defines a block as an intended same-vehicle trip chain. The recovered
weekday has 1,752 blocks and 1,087 simultaneous trips; 879 blocks interline.
There are 4,850 consecutive block transitions; none has nonpositive slack
across more than 0.5 km straight-line distance. Only three weekday transfers
offer at least 60 minutes. These checks support the block as a duty hypothesis,
not a vehicle identity, depot or charger record.

All 54,497 trips lack first-stop shape distance. The audit preserves a
monotonic interval; median width is 0.432 km and maximum 26.309 km. Energy
screens use the upper endpoint. The exact distance field remains null.

## Capacity classes and range screen

The 24/47/50/70/75/85 values are capacity signatures, not delivered bus
specifications. The 47/70 classes are retained as a route-level trolley proxy
only because the independent 2023 count has 262 trolleys. The source contains
no propulsion field. The 85 class is an inferred double-decker category and is
excluded from overnight-depot cost.

At a 300-km range, the 40-ft proxy requires 1,446 sequential duty requests for
1,244 base blocks; the 60-ft proxy requires 295 for 258. At 149/150 km they
require 2,032 and 412. Distance divided by range is a screening bound. It omits
vehicle exchange, garage travel, charger occupancy and spare policy, so it is
not a physical fleet count.

## Fleet scale bridge and scenario

The detailed 2022 category snapshot totals 1,711. The 2025 active fleet totals
1,733 and provides exact class and model-year sums, including 1,450 non-electric
or non-trolley vehicles. A derived 2023 total of 1,725 has interval 1,711--1,733.
The current policy case scales the 1,741 duty-request ratio to the derived
1,406 non-double-deck, non-trolley fleet, giving 1,630 battery positions and
1,612 net purchases after 18 existing BEBs.

The ordinary-renewal comparison renews a steady-state 10/17 of 1,388 fossil
positions, or 816 purchases. Vehicle capital, quoted 2023/2025 envelopes,
depot screening infrastructure, O&M and a 17-year straight-line vehicle
residual are discounted at 3%. The base gross project value is CAD 4.575
billion against CAD 2.329 billion, an economic score of -96.4%. A 50% grant
changes agency payment and score to CAD 2.710 billion and -16.4%; it does not
change resource cost.

The environmental boundary is production plus operation plus maintenance,
excluding depot/charger construction and end-of-life. It gives 29.2--82.4% reduction; the low end assumes renewable diesel and RNG across the conventional comparator. This is deliberately not called a complete life-cycle score.

## Direct limitations

- 2023 full-year timetable and actual operations are absent.
- Block-to-vehicle, block-to-garage and pull-out/pull-in records are absent.
- Vehicle age/payload, depot charger/grid capacities and trolley feeder data
  are absent.
- Candidate winter energy is a 2020 planning range; the Route 100 observed
  intensity's metering boundary is unresolved.
- The 2025 fleet table is retrospective evidence and includes 63 in-storage
  vehicles separately.
