# Parameter and evidence ledger (18 October 2026)

**Status vocabulary:** OBSERVED = stated in a primary source for the indicated year; HISTORICAL = a published older parameter, useful only for sensitivity; ASSUMPTION = explicitly chosen for a demonstration; MISSING = required for a city-wide verified result. Currency years are never silently mixed.

| Field | Value or state | Year / unit | Status | Source and use |
|---|---:|---|---|---|
| Primary metro eligibility | Vancouver CMA population 2,642,825 | 2021 census persons | OBSERVED | [Statistics Canada, 2021 CMA population table, released Feb 2022](https://www150.statcan.gc.ca/n1/daily-quotidien/220209/t002a-eng.htm); exceeds 500,000 threshold, not a 2023 ridership-demand forecast |
| TransLink route records | 191 distinct lines | 2023 routes | OBSERVED | [2023 TSPR CSV](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/csv-data/2023/tspr2023_bus_yearline.csv); includes route records, omits discontinued routes |
| Published bus route service | 5,466,190.5 | 2023 service hours | OBSERVED | Same CSV; sum of published route rows |
| Fixed-route bus actual service, excluding SeaBus | 5,575,772 hours; 106,868,324 service km; 5,715,791,401 capacity km | 2023 actual, reported 2025 | OBSERVED | [TransLink 2025 Business Plan, p. 23](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf): CMBC conventional/shuttle, West Vancouver and contract shuttle; derived by subtracting SeaBus from its published subtotal; calculation in `src/audit_service_actual.py` |
| Later 2025 Investment Plan bus-service trajectory | 2033 planned 4,424,000 bus hours; conditional 1,151,772 hours or 20.66% below 2023 actual; 2025--2034 planned total 50,049,000 hours | future plan approved 2025, thousands of hours | RETROSPECTIVE CONDITIONAL COMPARISON | [TransLink 2025 Investment Plan, Table A9 p. 63](https://www.translink.ca/-/media/translink/documents/plans-and-projects/ten-year-investment-plan/public-consultation/2025-investment-plan.pdf); `src/audit_service_floor.py`. Confirm A9 'Bus' and 2023 fixed-route actual service accounting are identical before claiming a strict like-for-like difference; this later trajectory is not an admissible no-service-cut comparator |
| Route-file hours / exact actual fixed-route bus hours | 98.035% | 2023 fraction | DERIVED | 5,466,190.5 / 5,575,772; stronger denominator than rounded statutory report |
| 2023 conventional bus actual service | 4,751,957 hours; 90,941,699 km; 5,274,956,916 capacity km | 2023 actual, reported 2025 | OBSERVED | Same Business Plan, p. 23; CMBC conventional category only |
| 2023 CMBC community shuttle actual service | 576,937 hours; 10,920,849 km; 262,100,376 capacity km | 2023 actual, reported 2025 | OBSERVED | Same source; separate from contracted community shuttles |
| 2023 West Vancouver/contract-shuttle actual service | 118,194 / 128,684 hours; 2,273,106 / 2,732,670 km; 113,076,825 / 65,657,284 capacity km | 2023 actual, reported 2025 | OBSERVED | Same source; both included in fixed-route bus boundary |
| Statutory bus service | 5,577,000 | 2023 service hours | OBSERVED | [2023 statutory report](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/statutory_annual_report/2023_statutory_annual_report.pdf): conventional 4,753k, shuttle 706k, West Vancouver 118k |
| Route data coverage of statutory hours | 98.013% | 2023 fraction | DERIVED | 5,466,190.5 / 5,577,000; denominator is three bus categories only |
| Route speed × revenue hours versus official service km | 93,740,872 km estimator / 106,868,324 km actual service | 2023 km | DERIVED / OBSERVED | The estimator is 87.716% of official actual bus service km; gap includes differing revenue/service scope and estimation error, **not solely deadhead** |
| Route time-bin frequency records | 6,261; 6,041 nonmissing | 2023 records | OBSERVED | [TSPR time-range CSV](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/csv-data/2023/tspr2023_bus_yearlinedaytypeseasontimerange.csv); not individual departures |
| Route-direction time-bin load records | 11,659; 9,371 nonmissing | 2023 records | OBSERVED | [TSPR peak-load CSV](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/tspr/csv-data/2023/tspr2023_bus_peakload_yearlinedaytypeseasontimerangedirection.csv); averages, not maximum load |
| Practical capacity by historical class | mini-bus 24; standard trolley 47; standard bus/coach 50; articulated trolley 70; articulated bus 75 | passengers/vehicle, 2018 guideline | HISTORICAL REFERENCE | [TransLink Transit Service Guidelines, pp. 21, 49](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/transit-oriented-communities/transit-services-guidelines-public-summary.pdf); capacity accounts for seated plus standing spaces, not a guaranteed candidate-BEB payload |
| Implied 2023 average capacity from load-factor denominator | 9,049/9,371 positive cells (96.56%) match 24, 47, 50, 70, 75 or 85; 322 unmatched; 34/180 routes have more than one label or an unmatched cell | passengers per aggregate route/direction/time-bin cell | DERIVED DIAGNOSTIC | `src/audit_capacity_proxy.py`, `results/capacity_proxy_audit.json`; 85 is **inferred**, not in the 2018 table, but consistent with [TransLink's 2017 double-deck pilot seating range 80--86](https://www.translink.ca/news/2017/november/translink%20launches%20double%20decker%20bus%20pilot%20project). Aggregated ratio cannot identify individual bus, block, or replacement capacity |
| Revenue-fleet operating GHG, all modes | 112,591 total; 110,402 Scope 1; 2,189 Scope 2; separate biogenic CO2 33,718 | tonnes CO2e except biogenic CO2 tonnes, 2023 | OBSERVED ALL-MODE ACCOUNTING | [TransLink 2023 Accountability Report, pp. 72 and 118--119](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/accountability_reports/2023/accountability_report_2023.pdf); includes bus and non-bus revenue vehicles, and excludes vehicle/infrastructure manufacture. Bus-only operating GHG cannot be read from this total; 110,402+2,189=112,591 |
| CNG buses | 299 | 2023 vehicles | OBSERVED | [2023 accountability report](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/accountability_reports/2023/accountability_report_2023.pdf), revenue-fleet section |
| Trolley plus battery-electric buses | 280 combined | Dec 2023 vehicles | OBSERVED | [TransLink, 14 Dec 2023](https://www.translink.ca/news/2023/december/metro%20vancouver%20diesel%20buses%20transitioning%20to%20cleaner%20renewable%20fuel); combined class only |
| Trolley buses | 262 | Feb 2023 vehicles | OBSERVED AT FEB DATE | [TransLink, 2 Feb 2023](https://www.translink.ca/news/2023/february/translink%20begins%20battery-electric%20bus%20fleet%20expansion); 188 standard, 74 articulated is the older configuration |
| Battery-electric buses | approximately 5 | Dec 2023 vehicles | OBSERVED APPROX. | [TransLink official December article](https://buzzer.translink.ca/2023/12/translink-shifts-buses-from-fossil-fuels-to-100-per-cent-renewable-diesel/) states about 275 trolleys and five BEBs; neither figure is an audited exact register |
| Electric fleet count inconsistency | 280 combined in December release; about 275+5 in same-day article; 262 trolley in February | 2023 vehicles | SOURCE CONFLICT | Subtracting February 262 from December 280 gives 18 BEBs only if trolley stock was unchanged; this contradicts the explicit December article. Use no exact December BEB count pending fleet register |
| 2023--24 procurement status | 46 articulated hybrids, 15 standard BEBs, 50 CNG, 168 shuttles, 25 double-deck | June 2023 project totals, vehicles | OBSERVED PROCUREMENT | [June 2023 Board packet, p. 11](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/board-of-directors/board-minutes-and-reports/2023/june/23-06-22-public-board-meeting-package---for-posting.pdf); 25 double-deck accepted with Q2 2023 timeline, other group totals mostly pending; not Dec fleet counts |
| 2020 plan total CMBC vehicles | 1,672 | historical vehicles | HISTORICAL | [2020 fleet transition plan](https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf); **not** a 2023 register |
| Existing trolleybuses | 188 standard + 74 articulated | historical vehicles | HISTORICAL | Same plan; these are already electric and should not be repurchased in a 2023 solution without an age register |
| 2021 static CMBC fleet snapshot | 466 hybrid; 401 diesel; 299 CNG; 262 trolley; 163 shuttle; 32 double-deck; 4 BEB, plus 46 contracted conventional and 43 contracted shuttle | Nov 2021 vehicles | HISTORICAL | [CMBC operating-company page](https://www.translink.ca/about%20us/about%20translink/operating%20companies/coast%20mountain%20bus%20company); explicitly dated Nov 2021, **not** a 2023 register and scope may differ from TSPR |
| 40-ft diesel / depot BEB purchase | 630,000 / 1,110,000 | 2019 CAD per vehicle | HISTORICAL | Same plan, cost appendix; BEB quoted with installed battery |
| Depot charging | 298,000 | 2019 CAD per 50-kW bus position | HISTORICAL | Same plan, Appendix D table D-1 and note 67: fully burdened charger price includes design, permitting, project management, financing and 10% construction contingency; count separate site works only where outside this scope, and separate financing transfers from real resources in a societal BCA |
| 40-ft depot BEB replacement ratio | 1.15 | 2020 planning ratio | HISTORICAL | Same plan; not a demonstrated 2023 route-specific result |
| Depot/class replacement ratios | standard 1.15--1.43; highway 1.36--1.66; articulated 1.13--1.55 across seven depots | 2020 modeled BEBs per old bus | HISTORICAL | Same plan, Appendix C Table C-2; assumes 500-kWh standard/660-kWh articulated batteries **and supplemental fuel heaters**. Its text estimates about 10% more BEBs with all-electric winter heat; not exact 2026 technology |
| 2026 articulated all-electric-heat stress | 49--67 buses for 39 retirements across hypothetical single-depot allocations; 4--22 over the 2025 plan's 45 | vehicles | DERIVED SCENARIO | `src/audit_capital_cohorts.py` multiplies Table C-2 articulated ratios by 1.10 then rounds up; depot assignment and 2026 technology unknown, so this is **not proof of actual shortage** |
| 40-ft historical lifetime-model costs | diesel 4.62; hybrid 4.77; CNG 4.15; all-electric in-route BEB 4.86; diesel-heated depot BEB 5.14 | 2019 CAD/vehicle-km | HISTORICAL | 2020 plan, Appendix D-2; include operator wages and capital assumptions; alternative **comparator** scenarios, never mix with 2024 O&M figures |
| 40-ft historical vehicle prices | diesel 630k; hybrid 890k; depot BEB 1,110k; in-route BEB 945k | 2019 CAD/vehicle | HISTORICAL | 2020 plan, Appendix D-1, MY2020 vehicles; initial batteries included; infrastructure separate |
| In-route charger and allocation | 450 kW, CAD 2.0m fully burdened, 1 charger per 8 buses | 2019 CAD; 2020 modeled site | HISTORICAL | 2020 plan, Appendix D-1; in-route price includes a small number of maintenance depot chargers; not universal station design |
| Diesel / depot BEB intensity | 0.60 L/km / 1.4 kWh/km **plus 0.02 L/km fuel heat** | 2020 planning values | HISTORICAL | Same plan, Appendix D table D-1; historical depot-BEB configuration is **not eligible** for the problem's strictly electric 2033 endpoint; all-electric cabin heating requires a different energy specification |
| Typical annual bus distance | 68,000 | km/bus/year | HISTORICAL | Same plan; per-bus example only |
| 2020 updated fleet program | 677 BEBs (585 standard, 92 articulated); CAD 236.9m incremental vehicle purchases, CAD 246.4m depot/charging investments | 2020--2029 award plan; nominal CAD | HISTORICAL PLAN | [Dec 2020 fleet-plan update](https://www.translink.ca/-/media/translink/media-releases/2021/january/translink_low_carbon_fleet_transition_plan_update_2021_01_18.pdf), Tables 1 and 3; its conventional normal-renewal **base case is hybrid replacements** for retiring diesel/hybrid buses, while 2021 CNG retirements were to get CNG replacements; **planned, not delivered**, and later facility dates changed |
| 2020 program operating savings and reconstructed nominal net | printed operating change −CAD 96.3m through 2030; annual printed cells sum −CAD 96.1m; reconstructed incremental net CAD 387.0m = 236.9+246.4−96.3 | 2020--2030 plan, nominal CAD millions | HISTORICAL PLAN / DERIVED | Same fleet-plan update Tables 1, 3 and 5; CAD 0.2m annual/total mismatch is consistent with display rounding or source precision. `src/audit_2020_program.py` checks award counts and costs. No infrastructure annual cashflow, so no justified NPV; 2020's 15 awards were funded in an earlier program |
| 2020 program planned awards by year | 2020:15; 2021:57; 2022:163; 2023:79; 2024:262; 2027:49; 2029:52; total 677 | planned award year, vehicles | HISTORICAL PLAN | Same update, Table 1; award is not delivery or in-service year. `data/processed/translink_2020_update_annual.csv` reproduces three vehicle categories and printed cost cells |
| 2020 updated facility targets | PTC 16 in-route chargers in two stages for 115 buses; MTC 280 depot chargers; BTC 267 depot chargers | 2023--2029 planned completion | HISTORICAL PLAN | Same update, Table 3; site allocation/total are planning quantities, not existing 2023 chargers |
| June 2023 electric-fleet snapshot | 4 BEBs and 262 trolleys at presentation date | June 2023 vehicles | OBSERVED DATE-SPECIFIC SNAPSHOT | [TransLink June 2023 Mayors' Council technology presentation, PDF p. 29](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf); distinct from the December combined count 280 and approximate five BEBs |
| June 2023 BEB and on-route charger screening prices | CAD 1.2m per BEB; CAD 460k--610k per on-route charger | June 2023 CAD, scope not fully itemized | HISTORICAL 2023 SCREEN | Same June presentation, PDF p. 28; price is a public screening figure, not an awarded bus quote or a fully burdened site-wide cost. Do not add battery cost without confirming quote scope |
| June 2023 depot and named charging project screens | new 500--600-fleet-equivalent depot CAD 1.2bn--1.8bn including land/development; Hamilton Route 100 charging CAD 2.3m planned 2024; PTC plus 10 on-route chargers CAD 46m planned 2025; Marpole CAD 500m to serve 340 BEBs planned 2026 | June 2023 CAD/program and target years | HISTORICAL 2023 PLAN | Same June presentation, PDF pp. 28--29. Planned dates and totals are not commissioned 2023 capacity; later 2024 ZEFTP targets supersede them. Depot program cost includes land and development, so dividing by bus capacity is not a hardware charger unit price |
| 2024 ZEFTP current plan facilities | PTC capacity over 100 BEBs targeted 2027; MTC about 340 BEBs targeted 2028 | vehicles/site and year | RETROSPECTIVE CHECK | [Nov 2024 ZEFTP, p. 12](https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf); supersedes old target dates, still not proof of commissioning |
| Charging construction lead time | 6--8 years at existing transit centres; commissioned 6--12 months before bus deliveries recommended | duration | RETROSPECTIVE CHECK | Same ZEFTP, p. 14; portfolio-level range, not a permit schedule for each depot |
| Grid expansion load | +78 MW by 2040, with seven on-route locations needing new distribution feeds | MW / sites | RETROSPECTIVE CHECK | Same ZEFTP, p. 14; full revenue-bus 2040 program, **not** fixed 2023 bus-service load |
| 2024 O&M costs | diesel 3.30; hybrid 1.97; CNG 2.77; BEB 2.28; trolley 4.12 | 2024 CAD/vehicle-km | RETROSPECTIVE CHECK | Same ZEFTP Attachment 3, pp. 18--19; includes maintenance, engine overhaul, fuel/electricity; excludes new vehicle and infrastructure capital |
| 2024 operating GHG | fossil diesel 1580; renewable diesel 530; fossil hybrid 1420; renewable hybrid 480; fossil CNG 1350; RNG 250; BEB electric heater 19; BEB hybrid diesel heater 28 | g CO2e/vehicle-km | RETROSPECTIVE CHECK | Same ZEFTP Attachment 3, pp. 18--19; operating boundary, not manufacture/lifecycle; renewable fuels excluded from all-electric endpoint |
| 2024 infrastructure envelope | new depots CAD 3.02bn; existing-depot expansion/electrification CAD 3.50bn; expanded bus infrastructure CAD 220m; up to 175 expansion BEBs CAD 370m | 2024 CAD, screening estimates | RETROSPECTIVE CHECK | Same ZEFTP, p. 13; −50%/+100% screening accuracy, **includes service expansion and multi-site works**, so not assignable directly to the 2023-service conversion cost |
| Identified retirement cohorts | 57 40-ft diesel-hybrids due 2023; 50 CNG due 2023; 126 40-ft diesel-hybrids due 2024; 30+6 40-ft diesel-hybrids and 9 Orion V coaches due 2025; 39 articulated diesels due 2026 | vehicle counts / expected useful-life year | RETROSPECTIVE CHECK | [TransLink 2025 Business Plan, pp. 50--51](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf); only identified capital projects, **not** a complete age register or proof of actual withdrawal |
| Trolley age/renewal cohorts | 188 standard trolleys entered service 2006--07; 73 articulated trolleys expected retirement 2028--29 | vehicle counts / years | RETROSPECTIVE CHECK | Same 2025 Business Plan, pp. 50--51; 188 replacement program and one pilot before 73 articulated replacements; 188+73=261, close to the Feb 2023 262 count but **not** proof of the remaining unit's age or current stock |
| Identified BEB replacement project quantities | 57 standard BEBs for 57 hybrid retirements (2023 program); 7 standard BEBs for 6 hybrid retirements (2025); 45 articulated BEBs for 39 diesel retirements (2026) | vehicles / named program | RETROSPECTIVE CHECK | Same 2025 Business Plan; planned ratios 1.00, 1.17 and 1.15 show why fleet size is not fixed one-for-one; **not** demonstrated trip-level adequacy or actual delivery dates |
| Later 2026 plan's 236-diesel replacement project | 39 60-ft diesel + 64 40-ft in-route BEBs + 153 40-ft depot BEBs = 256 planned replacements for 236 retiring diesels; gross project budget CAD 524.709m | 2026 named project, published later; vehicles and CAD millions | RETROSPECTIVE REVISION | [TransLink 2026 Business Plan, p. 51](https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2026-business-plan-operating-and-capital-budget.pdf); 256/236 = 1.085 vehicles per retirement. The older 2025 plan's 45 articulated BEBs for 39 diesels may overlap this revised cohort and **must not** be added to it; neither is an audited delivery |
| Later 2026 plan's 2028 hybrid cohort | 27 retiring 40-ft hybrids → 31 planned 40-ft BEBs; gross project budget CAD 59.320m | 2028 cohort in 2026 plan | RETROSPECTIVE PLAN | Same 2026 Business Plan p. 51; 31/27 = 1.148, not trip adequacy proof |
| Named non-electric replacement exposure before 2033 | 164 planned CNG in 2025 plan's 2023--2025 cohorts, plus 39 planned 60-ft diesel in later 2026 project = 203 across distinct named programs | planned vehicles, 2023--2026 retirement cohorts | DERIVED RETROSPECTIVE SCREEN | `src/audit_non_electric_lockin.py`; if procured and still operating, these need removal for a strict 2033 all-electric fleet. Does not prove actual delivery or exhaust all non-electric replacement plans |
| Illustrative 39-diesel early-retirement exposure | 39 × CAD 1.0m × 10/17 = CAD 22.94m before sale | historical 2019 CAD | ASSUMPTION-BASED STRESS | 2020 TransLink plan gives 17-year 40/60-ft bus life and approximately CAD 1.0m per 60-ft diesel. Assumes all 39 enter service start-2026 and retire start-2033; straight-line unused-capital proxy, **not** actual economic loss, delivered 2026 price or complete incremental cost. Salvage/redeployment and avoiding the 2026 purchase alter the comparison |
| 2023 57-BEB replacement project budget | gross CAD 106.846m; external funding CAD 102.498m; agency net CAD 4.348m | budget as reported in 2025 plan | RETROSPECTIVE CHECK | Same Business Plan, p. 50, table units CAD thousands; program budget, **not** a verified delivered 2023 unit price or just bus hardware; cannot infer 2023 fleet count from project title |
| Hypothetical 57-BEB project grant shares | 0/25/50%: agency payment CAD 106.846m / 80.135m / 53.423m, respectively; gross cost CAD 106.846m throughout | 2025-reported program envelope, CAD millions | DERIVED FUNDING SCENARIO | `src/audit_capital_cohorts.py`; assumes all project spending grant-eligible and ignores timing; **not** the full-fleet incremental economic score. Source-reported CAD 102.498m external funding is a separate retrospective budget entry, not the problem's ≤50% scenario |
| Bus life-cycle production factors | glider/powertrain 6.6 kg CO2e/kg; LFP battery 58 kg CO2e/kWh; diesel/BEB maintenance 52.4/67.5 g CO2e/km | 2024 methodological factors | TRANSFER SENSITIVITY | [ICCT 2024 e-bus LCA working paper](https://theicct.org/wp-content/uploads/2024/08/ID-118-%E2%80%93-E-bus-radar_final2.pdf), pp. 5, 10--11; Latin America average specifications, **not Vancouver measurements**; requires local vehicle masses, battery chemistry, capacity and replacement timing |
| ICCT 12--15 m example | 335 kWh battery; 14,880 kg BEB and 11,429 kg diesel glider/powertrain mass; 87-passenger modeled capacity | 2023 Latin America average, published 2024 | TRANSFER SENSITIVITY | Same paper, Table 3; an illustrative size-class prior only, not a TransLink bus specification |
| Integrated BC grid GHG intensity | 0.0113 | kg CO2e/kWh, 2023 | OBSERVED | [BC electricity factors](https://www2.gov.bc.ca/gov/content/environment/climate-change/data/electricity); average grid factor, not marginal construction/dispatch factor |
| CTA 2023 fixed-route bus baseline | 1,895 buses available for maximum service; 1,307 operated in maximum service; mean fleet age 11.2 years; 45,411,226 revenue miles = 73,082,284 km; 4,970,515 revenue hours; bus operating expenses USD 971,019,017 | 2023 actual | OBSERVED / DERIVED km | [FTA 2023 CTA agency profile, NTD 50066](https://www.transit.dot.gov/sites/fta.dot.gov/files/transit_agency_profile_doc/2023/50066.pdf), pp. 1--2; 45.0% reported spare ratio is system-level, not depot-specific; revenue miles/hours exclude deadhead; expenses cover all bus operation and are not electrification costs |
| CTA route count | 127 routes | FY2023 planning | OBSERVED APPROX. | [CTA FY23 budget](https://www.transitchicago.com/assets/1/6/FY23_Budget_Book_Final_Draft_%28For_Website%29.pdf); exact 2023 block register not established here |
| CTA 2023 year-end bus inventory and ages | 1,576 standard + 299 articulated = 1,875; weighted mean age 11.208 years; 1,056 aged 13+ and 539 aged 16+ | 2023 year-end stock | OBSERVED / DERIVED | [DOT NTD age distribution](https://data.transportation.gov/d/6abt-uhgq), filtered NTD ID 50066 and report year 2023; `src/audit_cta_2023.py` checks every age-bin sum. Year-end inventory is distinct from 1,895 VAMS and is not silently reconciled to it |
| CTA first-year fixed-availability renewal condition | assumed life cap 12/14/17 years requires at least 1,086/1,056/539 original slots renewed in 2024 | scenario counts, not agency rules | DERIVED AGE BOUND | Same age data and script; original stock at or above life cap after one year must renew if the cap is enforced. The chosen age bins give identical definite/possible bounds for these three caps. Charger and vehicle readiness must still be checked |
| CTA bus energy and matched mileage | diesel 13,573,058 US gal, 38,675,964 fuel-table miles; battery 479,980 kWh, 172,049 fuel-table miles | 2023 MB/DO | OBSERVED | [DOT NTD fuel and energy](https://data.transportation.gov/d/8ehq-7his), same year/agency filter; JSON source retained and hashed. Combined mileage is 85.55% of profile revenue miles, so source-scope reconciliation is still required |
| CTA matched-table energy intensities | diesel 0.82547 L/km; BEB charging 1.73349 kWh/km | annual averages, not winter peaks | DERIVED DIAGNOSTIC | `src/audit_cta_2023.py`; divide each energy quantity by its own reported propulsion mileage. Do not extrapolate to all profile bus service or treat as an all-electric winter guarantee |
| CTA 2023 BEB purchase announced | 22 additional buses | 2023 announcement | OBSERVED DECISION | [CTA release](https://www.transitchicago.com/cta-to-nearly-double-electric-bus-fleet/); purchase announcement is not proof of 2023 in-service vehicles |
| CTA June 2023 electric receipt stock and option price | 23 base-order buses already received, plus two earlier plug-in buses; June expansion from implied 25 to 47 with 22-bus option worth USD 26.2m | June 2023 receipt/contract state | DATED OBSERVATION | Same release explicitly confirms receipt of 23 and target 47 after 22 more; [FY24 budget](https://www.transitchicago.com/assets/1/6/FY24_Budget_Book_ADA_Accessible_Text.pdf) confirms two earlier plug-in buses. Does not prove 31 December in-service stock; contract envelope per bus is not full transition cost |
| TfL contracted fleet | 8,643 total, 950 electric, 20 hydrogen | 31 Mar 2023 vehicles | OBSERVED | [TfL fleet audit](https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf); 949 original electric + one retrofitted; hydrogen excluded from strict e-bus target |
| TfL vehicle types | 6,198 double-deck; 2,445 single-deck | 31 Mar 2023 vehicles | OBSERVED | Same TfL audit |
| TfL registration/body/propulsion cohorts | 17 registration years, 2007--2023; 8,643 total, 950 electric | 31 Mar 2023 stock | OBSERVED / RECONCILED | Detailed Tables 7--8 digitized in `london_2023_registration_cohorts.csv`. Table 2 prints SD total 2,447 and 2017 SD 341; detailed tables and fleet total instead reconcile to 2,445 and 339. The 2013 electric NRM was retrofitted in 2022 but its chassis age is retained |
| London optimized annual renewal capacity | life cap 12/14/17 years gives minimum peak 2,568/977/776 original fleet slots per year; total renewals 8,428/7,940/7,759 | 2024--2033, assumed chassis-life scenarios | EXECUTED CONDITIONAL MODEL | `src/optimize_london_cohorts.py`; all non-electric slots converted by 2033, same-body availability retained, existing EVs renewed when age-due. Zero integer-program gap; matches independent cumulative-deadline bound. These are fleet-slot planning counts, not route-feasible purchase quantities or asserted TfL life rules |
| Exact 2023 TransLink trips, vehicle blocks and depots | route/time-bin records available; 2023 GTFS archived by [Transitland](https://www.transit.land/feeds/f-c28-nstranslinkca), but historic ZIP download requires professional/enterprise API access | 2023 | PARTIAL / MISSING | GTFS could recover exact scheduled trips; GTFS generally lacks vehicle blocks, garage assignment and charging. Ask operator for duty extract |
| 2023 fleet by class, age, propulsion, depot | 280 electric combined, 299 CNG and 2023 procurement status confirmed; full class-age-depot register absent | 2023 | PARTIAL / MISSING | Needed to model retirement, remaining asset value and 2033 target; do not copy 2021 snapshot forward |
| Real 2023 delivered purchase prices, energy tariffs and charger site costs | April-2023 BC Hydro tariff and CAD 1.66/L budget diesel assumption now sourced; actual vehicle/site bids and invoices remain missing | 2023 CAD | PARTIAL | Historical tariff JSON and original 2023 budget retained; need site contracts and tender records; never blend 2019 nominal CAD with 2023 nominal CAD |
| Candidate double-decker and shuttle EV capacity/range in winter | not validated | 2023 technology | MISSING | 2024 TransLink playbook warns that shuttle blocks and double-decker deployment are late/technically difficult |
| Construction lead times, depot land/space and interconnection capacities | portfolio lead-time range and 2024 site targets known; 2023 site-by-site capacities missing | 2023--24 | PARTIAL / MISSING | Critical to proving a 2033 deadline; 2024 targets are retrospective checks |
| Battery production, vehicle manufacture, station construction/recycling GHG | ICCT transferable vehicle/battery/maintenance factors now identified; Vancouver bus mass/chemistry, actual replacements and station construction/recycling inventory missing | t CO2e | PARTIAL / MISSING | ICCT paper explicitly **excludes charging infrastructure and bus recycling**; cannot label its narrower result full life-cycle or silently transfer Latin America bus specifications |

## Treatment rules

### Newly resolved energy-price inputs

| Parameter | Value | Status and scope | Source |
|---|---|---|---|
| 2023 diesel purchase-price planning assumption | CAD 1.66/L | Original 2023 budget, not actual delivered price | TransLink 2023 Business Plan p. 17, `translink_2023_energy_budget.csv` |
| 2023 operational diesel planning volume | 32.17 million L | Broader system revenue/nonrevenue bus and WCE boundary; **not actual fixed-route bus-only use** | Same source |
| April-2023 RS1600 energy/demand/basic | CAD 0.0614/kWh, 12.50/kW/month, 0.2708/day | Secondary voltage, utility transformation; calendar-month benchmark | BC Hydro approved tariff printed pp. 2-35--2-38 |
| April-2023 RS1640 energy/demand | CAD 0.0756/kWh, 12.50/kW/month | Demand maximum during 06:00--22:00 only; physical grid power still required overnight; separately metered eligible fleet | Same tariff pp. 2-39--2-42 |
| April-2023 RS1650 energy/demand | CAD 0.0930/kWh, zero demand fee until 31 March 2026 | Dated transitional schedule, not constant through 2033 | Same tariff pp. 2-43--2-48 |
| April-2023 RS1901 rider | 1% refund | Applied before taxes/levies; parenthesized negative value verified by official 2023/24 statements | Same tariff p. 6-13 and BC Hydro financial statements note C |
| Historical all-electric heat/energy projections | 40-ft annual 1.37--2.00 kWh/km, mean 1.60; coldest-day mean 1.79; 60-ft annual/cold means 2.15/2.42 | 2020 modeled onboard propulsion plus cabin heat, not a current vehicle test; do not add heating again to these all-in intensities | TransLink 2020 Appendix C-1, PDF pp. 72--73 |
| Historical auxiliary demand examples | cooling about 2.5 kW at 27 C; resistance heat up to 14 kW at -18 C | Context-dependent engineering priors, not Vancouver measured fleet accessory profiles | Same source PDF p. 72 |

The tariff parameter JSON records the exact source URL/page numbers and direct
download limitation. `research/charging_tariff_note.md` explains the solved
charging relaxation, price-window crossover and remaining fleet-level limits.

1. The old vehicle's historical purchase price is sunk. Book only future operation, potential salvage or lost remaining service value, and new resource costs.
2. Grant percentages are transfer payments: project gross cost remains fixed; operator net payment falls by eligible grants.
3. Trolleybuses count toward electric service already delivered. Hybrid, CNG, renewable-fuel and hydrogen buses do not meet the problem's exclusive-electric propulsion-and-accessory definition.
4. A BEB using a diesel auxiliary heater does not satisfy the strict 2033 endpoint even if its main propulsion is electric. The 2024 TransLink technical recommendations discuss such heaters, creating an important feasibility tension.
5. Peak loads in the CSV are averages of peaks. They may guide prioritization, but exact peak-capacity preservation requires actual individual trips and a baseline vehicle-capacity roster.


## Energy-supply validation boundary (18 October 2026)

The executable validator now distinguishes battery, fuel and overhead supply.
The fuel comparator needs initial usable fuel, tank/reserve, consistent L or kg
and jointly calibrated winter distance/time consumption rates. No within-duty
refuelling is assumed. Existing trolley service requires certified wired paths
for trips and deadhead, powered stationary layovers, measured all-in peak draw
and commissioned firm feeder power after other loads/reserve. Reserving peak
power on every traversed feeder for a full moving segment is conservative; a
failed certificate is not proof of physical infeasibility under finer timing.
These are required data definitions, not newly observed Vancouver values.
Unknown fuel, path or feeder data remain missing. Depot spare checks now also
exclude buses driving to or returning from service. The arrival energy reserve
is tested before subsequent charging can restore energy.

## Fleet and fall-2023 timetable update

The source-declared TransLink GTFS version 23SEP_20231020 covers 4 September
through 31 December 2023. It contains 54,497 fixed-route bus trips, 1,684,516
bus stop-time rows and 25 calendar service patterns. Every trip has a source
block id, but the feed has no vehicle id, garage, propulsion, age, battery or
as-operated state. The first-stop shape distance is missing on all trips;
monotonic lower and upper distances are retained, with a median interval width
of 0.432 km.

The 2018 capacity clusters are treated only as 24/47/50/70/75/85 passenger
space proxies. They are never called delivered vehicle specifications. The
47/70 signatures are retained as a route-level trolley proxy because 262
trolleys are independently reported; this remains a proxy until an operator
route/vehicle roster is available.

The 18 November 2025 CMBC active fleet has 1,733 buses: 261 trolley, 22 battery,
535 hybrid, 365 CNG, 379 diesel and 171 gasoline shuttle. Its manufacture-year
counts total a further 63 in storage and reconcile exactly. A 2023 bridge is a
derived 1,725 with interval 1,711--1,733, not an observed 2023 roster. The 2025
age bands imply 392 active vehicles aged 0--4 and 543 aged 5--9; 285 were built
in 2023--2025, so accelerating all fossils to electric by 2033 creates material
early-retirement exposure.

## Full-class and uncertainty update (18 October 2026)

The class-specific core bound uses 1,424 heavy non-deck planning positions,
57 double-decks and 189 community shuttles. It retains the shared heavy-bus
depot investment once and adds only class-specific vehicle and charger
envelopes. Central gross present value is CAD 4.709 billion against CAD 2.458
billion for renewal plus operations (-91.6%); 25/50% grant cases are -53.6% and
-15.7%. The high class envelope is CAD 5.259 billion (-113.9%). The 1,424
positions are a transparent scaling of 1,630 generic non-deck positions after
removing the shuttle duty allowance; they are not a garage roster. See
`results/vancouver_full_fleet_bound.json`.

The 432,768-cell Cartesian assumption grid includes the 1,711--1,733 fleet
interval, seven paired range points, 5--18 retained BEBs, 9/17--11/17 renewal,
1.5--5.0% real discount, hardware/project vehicle costs and four fuel
intensities. It reproduces the named CAD 4.575-billion / -96.4% case exactly.
Equal-weight fifth/median/ninety-fifth economically scored cases are
-166.9/-127.2/-89.8%; environment scores are 13.3/72.6/82.4%. These are
assumption-space quantiles, never confidence intervals. See
`results/vancouver_transition_uncertainty.json`.

At a 700-kWh double-deck central case, 17 of 57 weekday duties have a
certain single-charge shortfall; the 827-kWh optimistic case still has eight.
A 150-kWh community shuttle has 49 of 101 certain shortfalls. These establish
the requirement for terminal or en-route charging; they do not certify a
specific stop or vehicle. See `results/deck_shuttle_electrification_audit.json`.

The regional economic layer uses the published 2023 Bus Operations umbrella:
CAD 945.537 million total expenditure, CAD 619.195 million wages and benefits,
and 72.5% BC supplier retention. Statistics Canada BS48A000 sector proxies give
an annual gross-value-added proxy of CAD 0.62--0.97 billion, labour income of
CAD 0.62--0.79 billion and 6.0--8.8 thousand FTE. Infrastructure is a separate
one-time gross activity memo (CAD 0.62--3.86 billion over 2024--31); it is not
added to annual operations. Vehicle manufacturing is excluded because BC
final assembly is unverified. See
`results/regional_and_air_quality_audit.json`.

The fixed-route tailpipe proxy allocates 106.868 million bus-km by fossil share
and fuel/stock proxies. It gives 126--408 t NOx, 1.11--8.34 t PM2.5 and
2.34--14.18 t PM10 per year. These are exhaust-only values; SeaBus, HandyDART,
rail, non-revenue vehicles, tire/brake wear and upstream fuel are excluded.
The underlying 2023 fuel-by-km split and emissions-control roster remain
unavailable.

APTA's public page lists `APTA-2023-Vehicle-Database`, but the ZIP returned a
Cloudflare challenge (HTTP 403); the report hash and TransLink rows remain
missing. The 2023 FOI log was obtained, but it contains no direct attachments
for the fleet-age/retirement requests. No APTA-derived counts were substituted
for the derived 1,711--1,733 bridge. See `research/apta_2023_fleet_note.md`.
