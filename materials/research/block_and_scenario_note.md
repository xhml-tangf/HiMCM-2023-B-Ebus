> **Priority revision (19 October 2026).** The emissions values below have
> been recomputed from the same annual service ramp as O&M and now read
> -17.6--15.1% (generic) and -14.3--16.2% (class subset) on the partial boundary.
> The purchase quantities are proportional inventory scenarios, not dispatch
> requirements; 1725 and 18 are unverified stock parameters. See
> `adversarial_review_resolution.md`.

# Fall-2023 blocks and conditional 2024--2033 scenario

## Source and semantics

The public mirror preserves TransLink GTFS 23SEP_20231020 at commit
eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b. Each downloaded file matches its
Git blob SHA-1 and has a SHA-256 in
data/processed/vancouver_gtfs_2023_provenance.json. The feed covers
2023-09-04 through 2023-12-31, not all of 2023 and not actual execution.

GTFS defines a block as an intended same-vehicle trip chain. The recovered
weekday has 1,752 blocks and 1,087 simultaneous trips; 879 blocks interline.
There are 20,679 consecutive block transitions and 4,850 route-changing
transfers; none has nonpositive slack
across more than 0.5 km straight-line distance. Only three weekday transfers
offer at least 60 minutes overall, while two route-changing transfers do.
These checks support the block as a duty hypothesis,
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
or non-trolley vehicles. The 2023 stock scenario selects 1,725 and varies 1,711--1,733; these are not observed stock or proven bounds.
The current policy case proportionally projects the upper-distance 1,741-of-1,698--1,741 request band
onto an assumed 1,401 non-double-deck, non-trolley stock, selecting 1,630
battery positions and 1,612 net purchases after 18 assumed existing BEBs.
This ratio is neither a lower nor upper vehicle bound; about five BEBs were
reported in service, so the grid also retains a 5--18 sensitivity.

The ordinary-renewal comparison renews a steady-state 10/17 of 1,388 fossil
positions, or 816 purchases. Vehicle capital, quoted 2023/2025 envelopes,
depot screening infrastructure, O&M and a 17-year straight-line vehicle
residual are discounted at 3% as constant-2023 CPI-rebased arithmetic with a real 3% rate, because the
public envelopes span 2021--2025 nominal years. The constant-2023 base gross value is CAD 4.303
billion against CAD 2.275 billion (-89.2%). Symmetric 25/50% grants give
-49.5/-9.8%; they do not change resource cost.

The environmental boundary is production plus operation plus maintenance,
excluding depot/charger construction and end-of-life. It gives -17.6--15.1% in the generic case; renewable fuel is negative because manufacturing exceeds the saving when conversion begins in 2030. This is deliberately not called a complete life-cycle score.

The class-specific follow-up brings 57 double-decks and 189 midpoint
community shuttles into one envelope while retaining shared heavy-bus depot
investment once, with 262 common trolley renewals included on both paths. Its
central constant-2023 PV is CAD 4.430 billion against CAD 2.625 billion for
renewal plus operations (-68.8%); the high vehicle case is CAD 4.726 billion
(-80.2%), and the partial-production score is -14.3--16.2%.
At 700 kWh for double-decks and 150 kWh for shuttles, 17/57 and
49/101 weekday duties respectively have a certain overnight-charge shortfall.
These are technical screens, not charger-site certificates.

## Direct limitations

- 2023 full-year timetable and actual operations are absent.
- Block-to-vehicle, block-to-garage and pull-out/pull-in records are absent.
- Vehicle age/payload, depot charger/grid capacities and trolley feeder data
  are absent.
- Candidate winter energy is a 2020 planning range; the Route 100 observed
  intensity's metering boundary is unresolved.
- The 2025 fleet table is retrospective evidence and includes 63 in-storage
  vehicles separately.
