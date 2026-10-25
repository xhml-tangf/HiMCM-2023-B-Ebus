# Vancouver official-evidence audit: fleet, depots, power and vehicle constraints

Access date: 2026-10-20. This note closes evidence that is available from
public authoritative sources. It does not promote a scenario to an observed
2023 fleet or certify a city-wide 2033 operating plan.

## What changed

1. The June 2023 TransLink presentation provides a dated capacity table and
   states that all CMBC bus depots were full. The older 2020 fleet plan gives
   the actual per-centre nominal capacities and class allocations.
2. A later 2024 TransLink analysis gives system-wide power evidence: 78 MW of
   additional load by 2040, a BC Hydro adequacy statement for centres before
   2035 and on-route chargers before 2030, and explicit new-feed requirements.
3. Official vehicle specifications support the battery, charging, passenger
   capacity and winter-range assumptions at a product/prototype level. They do
   not establish route payload, kWh/km or local winter certification.
4. The exact end-2023 fleet register remains unavailable. The current 18-BEB
   initial scenario is not the best public central estimate: the December 2023
   official operator blog reports approximately 275 trolleys and five BEBs,
   while the agency states an exact combined electric total of 280.

## Fleet evidence

| Date | Public evidence | Status for the model |
|---|---|---|
| 2023-02-02 | 15 Nova LFSe+ buses ordered; the BEB fleet is planned to grow from four to 19 over the following year | Official procurement/ramp statement; not an end-2023 in-service register. [TransLink release](https://www.translink.ca/news/2023/february/translink%20begins%20battery-electric%20bus%20fleet%20expansion) |
| 2023-06 | Four BEBs and 262 trolleys in service | Dated presentation, not a December stock split. [June 2023 agenda](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf), p. 30 |
| 2023-12-14 | Exact total of 280 trolley-electric and battery-electric buses | Official aggregate. [TransLink release](https://www.translink.ca/news/2023/december/metro%20vancouver%20diesel%20buses%20transitioning%20to%20cleaner%20renewable%20fuel) |
| 2023-12-14 | Approximately 275 trolley-electric and five battery-electric buses | Official approximate split. [The Buzzer](https://buzzer.translink.ca/2023/12/translink-shifts-buses-from-fossil-fuels-to-100-per-cent-renewable-diesel/) |
| 2025-11-18 | 1,733 active and 63 stored CMBC vehicles, by site and propulsion | Retrospective snapshot; not a 2023 roster. [FOI status table](https://www.translink.ca/-/media/translink/documents/about-translink/freedom-of-information/cmbc-fleet--active--instorage.pdf) |

The 2023 FOI inventory shows that records exist for retired vehicles, spare
buses, peak deployment, operator sign-up sheets, new fleet numbers and
block-to-GTFS mapping (requests 2023-249, -327, -375, -409, -411, -739 and
-829). The public request log records them as released in full, but it does not
publish the attachments: no URIs or embedded files are present. This is a
publication gap, not evidence that the underlying records do not exist.

The APTA 2023 official vehicle-database ZIP remains unavailable: the public
endpoint returns HTTP 403 for the archive. No APTA row is inferred.

## Depot evidence

The 2020 fleet plan lists six operating CMBC centres with a combined 1,991
nominal 40-foot-equivalent spaces and Marpole planned at another 300. The direct
CMBC allocation is 1,538; 134 contractor vehicles make its 1,672 total. These
are 2020 capacities and assignments, not 2023 occupancy.

| Centre | Nominal 40-ft-equivalent capacity | 2020 assigned direct stock |
|---|---:|---:|
| Burnaby | 312 | 242 |
| Hamilton | 296 | 185 |
| Port Coquitlam | 288 | 203 |
| Richmond | 271 | 212 |
| Surrey | 285 | 249 |
| Vancouver | 539 | 447 |
| Marpole | 300 planned | not open |

Source: [Low Carbon Fleet Transition Plan, 2020](https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf),
Table 3, p. 14 and footnote 8. The table also confirms that all 262 trolleys
were assigned to Vancouver and that the other centres mixed 40- and 60-foot
buses.

The June 2023 presentation separately states that all depots are full and that
only one supports BEBs, one supports trolleys and three support natural gas.
The associated report estimates an additional 2,000 bus spaces, nearly a 90%
increase, by 2035, with capacity reached in 2026/27 and recent depot projects
taking 6+ years. See the same [June agenda](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf),
pp. 20 and 40-42.

The nominal total is not an operational capacity certificate. The 2025 snapshot
has 1,733 active buses, below the 2,291 nominal total including planned Marpole,
yet the 2023 operator statement already described the system as full. Track
mix, clearances, fuelling, maintenance, charging, spare policy and staged
construction must be checked per site.

## Charging and electrical power

| Evidence | Finding | Limitation |
|---|---|---|
| 2023 June screen | Hamilton includes depot plug-in chargers and one in-route charger for CAD 2.3m; PTC plus ten in-route chargers is screened at CAD 46m; Marpole is CAD 500m for 340 BEBs | Planned envelopes and dates, not commissioned assets |
| 2024 zero-emission fleet plan | Full transition adds 78 MW by 2040 | System-level, not site firm capacity |
| BC Hydro adequacy statement | Forecast can be met for centres transitioning before 2035 and on-route chargers required before 2030 | New feeds required after 2035, at new centres and for seven on-route locations; future power cannot be reserved or guaranteed |
| Project delivery | Existing-centre charging takes 6-8 years and should precede buses by 6-12 months | A 2033 endpoint needs power projects beginning well before 2024/25 |

Source: [November 2024 Mayors' Council package](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf),
pp. 12-14. The 78 MW is evidence about the utility connection required for the
2040 plan. It does not identify a depot transformer, feeder, firm MW, or a
commissioned date for the accelerated 2033 scenario.

## Vehicle specifications and payload

### Nova LFSe+

The official brochure gives up to 564 kWh, a maximum 450 kW overhead or 150 kW
plug-in charge, and less than 3.25 hours for a full depot charge. It also gives
up to 41 seats and 68 total passengers in the four-battery configuration, but
only 59 total passengers in the six-battery configuration. The battery/range
trade-off is therefore explicit. Source:
[Nova LFSe+ brochure, March 2021](https://us.novabus.com/wp-content/uploads/sites/2/2019/10/LFSe_brochure_march2021_EN.pdf),
pp. 1-2.

TransLink's November 2022 prototype report says the LFSe+ travelled more than
150 km on one charge even during winter, versus about 40 km for the earlier
test bus. Its existing overhead chargers topped up in under six minutes. This
supports a roughly 150 km lower-range screen for a prototype, not a fleet-wide
winter energy profile. Source:
[TransLink Buzzer](https://buzzer.translink.ca/2022/11/our-new-battery-electric-bus-arrives-in-metro-vancouver/).

The 2020 plan gives a 40-foot BEB GVWR of 19,550-20,450 kg and curb weight of
12,100-15,350 kg. Relative to a diesel bus, depot-charged battery buses add
1,800-2,700 kg, with 1,200-1,800 kg on the rear axle; in-route-charged buses
add 450-1,150 kg. It notes that allowable pack size may be limited by axle
weight. These ranges support the need for a payload test; they do not establish
the payload on a particular TransLink route.

### Double-deck and shuttle candidates

The November 2023 Enviro500EV Hong Kong technical sheet specifies 472 kWh,
150 kW DC plug charging, 82 seats, 117 total passengers, two wheelchair spaces
and a heat pump, with range expressly dependant on duty cycle. It is not a
North American three-axle configuration or a TransLink winter test. Source:
[Enviro500EV specification](https://www.alexander-dennis.com/site-content/uploads/2023/10/Enviro500EV-Hong-Kong-2023-11.pdf),
p. 2.

The 2025 Letenda test has 22 seats, 44 maximum passengers, about 250 km range
and a 150 kW charge in about two hours. It is later than 2023 and cannot supply
a 2023 community-shuttle one-for-one design. Source:
[TransLink trial](https://buzzer.translink.ca/2025/03/were-testing-a-30-foot-battery-electric-bus/).
The 2024 operator plan recommends beginning shuttle conversion only in the
mid-2030s because most current blocks are not feasible electrically.

## Trolley feeder evidence

Official operator material reports 262 trolleys, about 320 km of overhead,
600 V DC and 20-22 rectifier stations depending on the publication date. A 2025
guidance document says a system branch can carry up to 3,000 A. This establishes
the system architecture and a broad branch-capacity clue. It does not provide
the simultaneous firm capacity of each feeder segment or the feeder paths used
by each trolley block. Source:
[trolley overhead construction guidance](https://www.translink.ca/-/media/translink/documents/business-with-translink/real-estate/instructions-to-employers-when-planning-work-in-proximity-to-the-TOH-system-final.pdf),
p. 1; [2023 system facts](https://buzzer.translink.ca/2023/08/75-facts-about-trolleybus/).

## Model consequences

1. Five BEBs and about 275 trolleys is the closest public 2023 split. Keep the
   current 18-BEB case only as a stress scenario. If the route-position total is
   held fixed, switching to five retained BEBs adds 13 route purchases and the
   trolley-renewal count rises by 13; the cost should be recomputed rather than
   treating the two substitutions as free.

   The retained model instead preserves the fixed 1,725 scenario total and the
   1909 known purchase schedule: its central split is 275 trolleys plus five
   BEBs, while 13 initial electric assets are explicitly carried through 2033
   because the public split is approximate and the identified trolley renewal
   schedule contains 262 vehicles. If those 13 also need replacement, the plan
   requires 13 additional purchases.
2. The 1,927 2033 electric-asset endpoint does not exceed the 2020 nominal
   space total including Marpole, but it cannot be certified by that arithmetic.
   All depots being full in 2023 and mixed-equipment constraints mean that a
   site-by-class allocation remains necessary.
3. The 78 MW system result is useful evidence, but facility firm capacity and
   transformer/feeder timing remain missing. The accelerated 2033 case still
   needs earlier commissioning than the published 2040 path.
4. The LFSe+ winter prototype supports the lower end of the range screen. It
   does not validate 300 or 350 km for the 15-bus fleet, nor full passenger load.
5. The double-deck and shuttle evidence still does not close the route-level
   payload, winter energy, curb geometry or terminal dwell constraints.

## Remaining public-data gaps

- A 31 December 2023 vehicle register by class, age, depot, status and propulsion.
- The public attachments for FOI 2023-249/327/375/409/411/739/829.
- Authentic block-to-vehicle and block-to-garage assignments for every trip.
- Depot occupancy, bus/charger footprint, transformer and feeder limits.
- Site firm power, interconnection cost and actual commissioning dates.
- Route-level winter kWh/km, electric-heater load, payload and axle approval.
- Trolley feeder/rectifier concurrent capacity by segment.
- Full-year 2023 as-operated times and passenger loads.

## Files and reproduction

- `materials/research/audit_vancouver_official_evidence_v3.py`: rechecks local source
  hashes, key phrases and depot totals.
- `materials/research/data/processed/vancouver_official_evidence_v3.csv`: curated source
  observations and limitations.
- `materials/research/data/processed/vancouver_depot_capacity_2020.csv`: per-centre table.
- `materials/research/data/processed/vancouver_vehicle_specs_v3.csv`: vehicle evidence.
- `materials/research/data/processed/vancouver_official_evidence_v3.json`: generated
  audit result and source hashes.

The local core documents have these SHA-256 digests: 2020 fleet plan
`1042fbcf...5ec15`; June 2023 technology package `9e188c6d...d01085a`;
June 2023 Board package `6921d8cc...0226623d`; November 2024 playbook
`00c6d662...bf96098`. The FOI 2023 log is `60c61527...5fc1fba` and the
2025-11-18 CMBC scan is `be0d3cd5...f839b2`. Full values are in the generated
JSON audit result.

Run:

```powershell
python materials/research/audit_vancouver_official_evidence_v3.py
```
