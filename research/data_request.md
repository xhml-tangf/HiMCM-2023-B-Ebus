# Minimum data request to close the numerical model

Public work has narrowed this request: 2023 reporting fixes 280 trolley/BEB
vehicles together and 299 CNG vehicles. A same-day official article reports
approximately five BEBs; the 18 delivered vehicles are compatible with the
aggregate 280, but exact year-end in-service status remains unobserved. A
2025-11-18 CMBC table provides 1,733 active vehicles by propulsion, site and
manufacture year, while a detailed 2022 category snapshot gives 1,711. These
support a derived 2023 total of 1,725 with interval 1,711--1,733, never a
claimed observed roster. The 2025 capital plan identifies
selected retirement cohorts and project budgets; the 2020 fleet study supplies
historical depot/class replacement ratios; and the 2024 transition review
supplies facility target dates and a six-to-eight-year delivery range. These
are recorded with year and status in `parameter_ledger.md`. The 2025 plan also
reports 2023 actual fixed-route bus service totals of 5,575,772 hours,
106,868,324 km and 5,715,791,401 capacity-km after excluding SeaBus; see
`results/actual_service_audit.json`. The fall-2023 GTFS adds 54,497 trips, 25 calendar patterns and source-declared blocks. The original 2023 budget supplies a diesel planning price, and approved April-2023 BC Hydro rates supply charging windows, demand charges and the rate rider. These do not provide the full-year as-operated record, installed-site electrical capacity or matched life-cycle inventory.

Ask TransLink/CMBC for a 2023 frozen extract, with schema and units, covering:

1. **Fleet on 31 December 2023:** vehicle ID, fixed-route status, class (40-ft, 60-ft, coach, double-deck, shuttle, trolley), propulsion, depot, in-service year, seating/standing/accessibility capacity, expected retirement, operational availability, electric battery and heater type. De-identify vehicle IDs consistently if necessary.
2. **Service blocks:** the remaining January--August 2023 schedule versions and the as-operated record, with trip, route, direction, exact times, stop/terminal locations, distance, source block, pull-out/pull-in, passenger load and actual vehicle. The recovered fall GTFS supplies planned trips and block hypotheses but no vehicle or garage link.
3. **Depot/charger inventory:** bus/charger parking capacity, existing installed charger count/power/connector, transformer and feeder limits, actual load profile, construction/design lead times, and utility interconnection constraints by site.
4. **Candidate vehicles and bids:** delivered 2023-price-year CAD cost including battery, battery usable energy, winter kWh/km with fully electric heat, certified passenger capacity, charge curve, warranty/life, spares, replacement battery cost, charger proposals and all-in construction scopes.
5. **Comparable operating ledgers:** 2023 total bus service-km and capacity-km are public, but fuel/electricity by vehicle class, maintenance and operator hours, site-specific metering, selected BC Hydro schedule and actual billed demand (the published April-2023 tariffs are now sourced), contractor costs, salvage proceeds and approved grants remain needed. Use ordinary renewal as the comparison, not the historical purchase price of the existing bus.
6. **Life-cycle factors:** consistent scope for vehicle/battery production, charger/depot/grid construction, fuel upstream/combustion, electricity average and marginal scenarios, maintenance and end of life; report tailpipe NOx and PM separately.

Release gate: only after these fields pass the paper's three checks can the null values in `results/model_readiness.json` be replaced by validated 2024-2033 purchases, gross and agency costs, life-cycle scores and a Pareto frontier.
