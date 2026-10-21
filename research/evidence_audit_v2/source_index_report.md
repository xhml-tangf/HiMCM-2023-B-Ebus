# Source and research-material index

Scope: 2023 HiMCM Problem B electric-bus study. This index was built without
using any original 2023 HiMCM solution paper and without treating the current
model's assumptions as observations. The machine-readable list is
`source_index.csv`; it contains 86 records, 43 of which have a retained local
path and computed SHA-256. `build_source_index.py` regenerates the CSV and local
hashes.

## Coverage by evidence family

| Family | Key retained material | What it can establish |
|---|---|---|
| Vancouver timetable and service | 2023 GTFS; 2023 TSPR annual, time-range and peak-load CSV; 2023 actual service table in 2025 Business Plan | Scheduled trips, routes, calendar patterns, source block IDs, time-bin frequency and load-factor proxies, annual service totals |
| Vancouver fleet and facilities | 2020 fleet plan; 2023 June Board and technology presentations; 2024 transition plan; 2025 and 2026 Business Plans; 2025 CMBC snapshot | Historical fleet structure, nominal depot spaces, selected retirement cohorts, project and power envelopes, later snapshots |
| Vancouver environment and prices | 2023 Accountability Report; 2023/24 BC Hydro statements; 2023 BC Hydro tariff; BC grid factors; Bank of Canada CPI | Operating emissions, fuel/energy context, electricity prices, macro rebasing |
| Vehicle technology | Nova LFSe+; Winnipeg RFP; New Flyer; Alexander Dennis; Foothill; GreenPower; Endera | Manufacturer or procurement specifications for battery, charge, mass and passenger capacity |
| Chicago | CTA budgets; Charging Forward; 2023 expansion release; FTA profile; NTD age and fuel/energy datasets | 2023 fleet scale, age bins, reported service and matched fuel/BEB energy samples |
| London | TfL fleet audit | 2023 vehicle counts by body, propulsion and registration year |
| Independent methods and LCA | Rogge 2018; Pelletier 2019; Gkiotsalitis 2023; TRD 2023; ICCT 2024; Zhao 2022; Yeboah 2025 | Method transfer and non-local life-cycle or emission-factor assumptions |
| Regional economics | Statistics Canada input-output; Transport Canada compensation | Separate regional value-added, multiplier and labour context |
| Air quality | EEA guidebook; BC regional inventory report | Separate NOx and particulate method and parameter evidence |
| Contest format | COMAP public 2024 examples and 2025 results pages | Format evidence only; not operational data and not a 2023 solution |

## Highest-value data assets

### Directly usable observed service data

The strongest empirical asset is the combination of the fall-2023 GTFS and the
three 2023 TSPR tables. GTFS provides 54,497 fixed-route bus trips across 25
service patterns, with trip times, routes, directions, endpoint geometry and
source-declared blocks. It does **not** provide vehicle IDs, garage assignment,
age, propulsion, battery state, actual passenger loading or as-operated times.

The TSPR annual table supplies 191 published route records and 5,466,190.5 route
service-hours. The 2025 Business Plan independently reports 2023 fixed-route bus
actuals excluding SeaBus: 5,575,772 hours, 106,868,324 service-km and
5,715,791,401 capacity-km. These have different boundaries and dates of
publication; they are useful for reconciliation, not interchangeable fields.

The time-range table has 6,261 records, 6,041 with nonmissing values. The peak-
load table has 11,659 records, 9,371 with nonmissing values. Positive load cells
are consistent with one of six reference capacities in 96.56% of cases. Those
capacity signatures describe aggregate route/time-bin averages; they cannot
identify the bus assigned to a trip.

### Usable official fleet facts and their limits

- The December 2023 aggregate is 280 trolley plus battery-electric buses.
- A same-day operator article gives approximately 275 trolleys and five BEBs.
- The 2023 Accountability Report gives 299 CNG buses and 112,591 t CO2e of
  revenue-fleet operating emissions across all modes.
- A November 2025 CMBC summary gives 1,733 active and 63 stored vehicles by
  site, propulsion and manufacture-year bins. It is retrospective and must not
  be copied backwards as a 2023 roster.
- The 2020 plan gives six operating centres with 1,991 nominal 40-ft equivalent
  spaces and a planned 300-space Marpole facility, but the 2023 operator
  statement already called the depots full. Nominal space is not vacant space.

Therefore the evidence supports historical and cross-sectional fleet analysis,
selected cohort accounting and bounded scenarios. It does not identify the
actual 31 December 2023 fleet by individual class, age and garage.

### High-value infrastructure and cost envelopes

The June 2023 technology update gives dated screening envelopes, not bids:

- generic BEB approximately CAD 1.2 million;
- on-route charger equipment approximately CAD 0.46--0.61 million;
- Marpole screening concept CAD 500 million for 340 BEB positions;
- Hamilton Route 100 package CAD 2.3 million;
- Port Coquitlam plus ten on-route chargers CAD 46 million.

The 2024 transition plan adds 78 MW of system load for a 2040 full transition,
six-to-eight-year existing-centre charging delivery, and a six-to-twelve-month
lead between site charging and buses. These are valuable scale constraints, but
they do not provide site-by-site firm power or a 2033 interconnection schedule.

The 2025 plan identifies selected retirement and replacement cohorts. The 2026
plan revises overlapping projects. These cohorts can test whether a stated
purchase program is internally large enough, but they are not a complete age
register or delivery record.

### Vehicle specifications and experimental evidence

Manufacturer and procurement documents provide several concrete envelopes:

- Nova LFSe+: up to 564 kWh, 450 kW overhead or 150 kW plug, 41 seats, and 68
  versus 59 total passengers depending on battery configuration.
- Winnipeg XE40/XE60: 432/605 kWh, 90% manufacturer usable capacity, 14,905 and
  23,453 kg curb mass.
- Enviro500EV Hong Kong: 472 kWh, 150 kW DC, 82 seats, 117 total passengers.
- Foothill 2024 contract: USD 1.758 million per double-decker, with a later
  product claim of over 700 kWh and about 2 kWh per mile.
- GreenPower EV Star: 19 passengers plus driver, 118 kWh, 150-mile nominal range.
- Endera 2023: 150 kWh electric shuttle.

TransLink's 2022 LFSe+ prototype report says the bus exceeded 150 km on one
charge in winter, but it supplies neither route-level kWh/km nor a full-load
payload/axle result. Rated manufacturer capacity is not an observed winter
duty-cycle capability.

### Chicago and London

Chicago has a usable fleet/age/energy register: 1,875 buses at year-end 2023 in
the NTD file, age bins down to 16+, and fuel/BEB energy rows whose matched
mileage covers 85.55% of the annual profile revenue miles. It lacks
vehicle-to-block assignments, depot capacity and firm power in the retained
public evidence.

London has a strong 31 March 2023 fleet audit: 8,643 positions, split into 2,445
single-deck and 6,198 double-deck bodies, with 950 electric and 20 hydrogen
vehicles and registration cohorts from 2007 through 2023. It lacks route blocks,
depot electrical capacity and operator-specific costs in the retained evidence.

## Environmental and economic evidence

The grid factor 0.0113 kg CO2e/kWh is an official annual average, not an hourly
zero-emission certificate. BC Hydro's Clean Electricity Standard portfolio does
not prove that every charger is backed hour-by-hour by a clean source.

The ICCT 2024 factors are transferable method parameters: 6.6 kg CO2e/kg for a
glider/powertrain, 58 kg CO2e/kWh for LFP cells, and 52.4/67.5 g CO2e/km for
diesel/BEB maintenance. They come from a Latin American average and exclude
charging infrastructure and bus recycling. They cannot be called a Vancouver
life-cycle inventory.

The 2023 BC Hydro tariff provides detailed energy, demand and basic charges plus
a 1% rider refund. The approved PDF was blocked for direct download, but the
structured values and original URL/page locators are retained. Site-specific
interconnection, transformer and utility upgrade bids remain absent.

## Evidence-grade conclusion

| Evidence grade | Examples | Decision use |
|---|---|---|
| A: downloadable primary dataset | GTFS, TSPR CSV, NTD Chicago API, TfL audit, tariff values | Direct analysis with stated schema/boundary |
| B: dated official source | fleet notices, business plans, public board/technology reports, BC grid factor, CPI | Quantitative fact with historical/scope caveat |
| C: manufacturer or procurement specification | Nova, New Flyer, Winnipeg, Enfield/ADL, Foothill, Endera, GreenPower | Equipment envelope only; not local operation |
| D: transfer estimate | ICCT, EEA, regional input-output, external city prices | Sensitivity or method input unless localized |
| E: blocked or absent | full 2023 vehicle-age-depot register, vehicle-block-garage mapping, depot firm power, route winter telemetry, strict clean-energy certificates, local item bids | Cannot support a direct factual claim |

The evidence can support a defensible study of published-service preservation,
fleet-count lower bounds, annual service and capacity reconciliation, scenario
cost envelopes, charging infrastructure scale, cross-city vehicle-age cohorts,
and transparent sensitivity analyses. It cannot by itself certify a
city-specific 2033 purchase-and-dispatch plan, exact route energy, exact depot
power availability, local fleet life-cycle emissions or an awarded cost.

The index deliberately preserves links and local paths for material that was
not used in the newest model. A fact remains available even if the model that
first used it is discarded.
