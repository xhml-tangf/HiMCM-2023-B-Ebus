# Minimum data request to close the numerical model

Public work has narrowed this request: 2023 reporting fixes 280 trolley/BEB
vehicles together and 299 CNG vehicles. A same-day official article reports
approximately five BEBs, but the implied trolley count conflicts with a
February notice. The 2025 capital plan identifies
selected retirement cohorts and project budgets; the 2020 fleet study supplies
historical depot/class replacement ratios; and the 2024 transition review
supplies facility target dates and a six-to-eight-year delivery range. These
are recorded with year and status in `parameter_ledger.md`. The 2025 plan also
reports 2023 actual fixed-route bus service totals of 5,575,772 hours,
106,868,324 km and 5,715,791,401 capacity-km after excluding SeaBus; see
`results/actual_service_audit.json`. These do not provide a complete 2023 duty
roster, installed-site electrical capacity or matched life-cycle inventory.

Ask TransLink/CMBC for a 2023 frozen extract, with schema and units, covering:

1. **Fleet on 31 December 2023:** vehicle ID, fixed-route status, class (40-ft, 60-ft, coach, double-deck, shuttle, trolley), propulsion, depot, in-service year, seating/standing/accessibility capacity, expected retirement, operational availability, electric battery and heater type. De-identify vehicle IDs consistently if necessary.
2. **Service blocks:** every 2023 representative weekday/Saturday/Sunday/winter trip ID with route, direction, exact departure/arrival times, stop/terminal locations, distance and assigned vehicle block; schedule variants and deadhead/pull-out/pull-in legs. Link a baseline peak passenger load or required capacity to each trip. An archived 2023 GTFS export helps with trips but may not include duty blocks or depots.
3. **Depot/charger inventory:** bus/charger parking capacity, existing installed charger count/power/connector, transformer and feeder limits, actual load profile, construction/design lead times, and utility interconnection constraints by site.
4. **Candidate vehicles and bids:** delivered 2023-price-year CAD cost including battery, battery usable energy, winter kWh/km with fully electric heat, certified passenger capacity, charge curve, warranty/life, spares, replacement battery cost, charger proposals and all-in construction scopes.
5. **Comparable operating ledgers:** 2023 total bus service-km and capacity-km are public, but fuel/electricity by vehicle class, maintenance and operator hours, BC Hydro tariff and demand charges, contractor costs, salvage proceeds and approved grants remain needed. Use ordinary renewal as the comparison, not the historical purchase price of the existing bus.
6. **Life-cycle factors:** consistent scope for vehicle/battery production, charger/depot/grid construction, fuel upstream/combustion, electricity average and marginal scenarios, maintenance and end of life; report tailpipe NOx and PM separately.

Release gate: only after these fields pass the paper's three checks can the null values in `results/model_readiness.json` be replaced by validated 2024-2033 purchases, gross and agency costs, life-cycle scores and a Pareto frontier.
