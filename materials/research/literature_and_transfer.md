# Independent literature and three-city transfer

No 2023 HiMCM submissions or solution papers were used.

| Work | Model/data contribution | Implication for this study |
|---|---|---|
| [Rogge et al., *Applied Energy* 211 (2018), 282–295](https://orbit.dtu.dk/en/publications/electric-bus-fleet-size-and-mix-problem-with-optimization-of-char/) | Joint electric fleet size/mix, charging infrastructure and vehicle scheduling; operating and extra-bus costs matter. | Link purchases to feasible schedules; do not assume one-for-one replacement. |
| [Pelletier et al., *Transportation Research C* 109 (2019), 174–193](https://researchportal.bath.ac.uk/en/publications/the-electric-bus-fleet-transition-problem/) | Multi-period integer program for purchases, salvage, operation, stations and electricity demand charges. | Use a 2024–2033 cohort transition, with gross and subsidized cost views. |
| [Gkiotsalitis, Iliopoulou & Kepaptsoglou, *EJOR* 306 (2023), 189–206](https://research.utwente.nl/files/352082622/1-s2.0-S0377221722005707-main.pdf) | Exact multi-depot electric scheduling with time windows, travel and charging. | Assignment, SOC, interlining and charger concurrency require trip/block detail. |
| [Joint optimization of electric bus charging, scheduling and management, *Transportation Research D* 117 (2023)](https://doi.org/10.1016/j.trd.2023.103653) | Integrates charger and charge timing with vehicle blocks and tariffs. | Separate depot and opportunity charging as alternatives, respecting grid and timetable constraints. |

## Transfer cases

**Chicago CTA.** The [FY23 budget](https://www.transitchicago.com/assets/1/6/FY23_Budget_Book_Final_Draft_%28For_Website%29.pdf) gives a >1,800 bus, 127-route system. The [Charging Forward report](https://www.transitchicago.com/assets/1/6/Charging_Forward_Report_2-10-22_%28FINAL%29.pdf) has garage sequencing and a 2040 target. The [June 2023 announcement](https://www.transitchicago.com/cta-to-nearly-double-electric-bus-fleet/) covers 22 additional BEBs but does not establish that those vehicles entered service in 2023. The same optimization structure transfers; vehicle life, winter heating, Illinois generation and utility demand charges need local values. Exact 2023 blocks and age cohorts still need acquisition.

**London TfL.** The [31 March 2023 audit](https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf) gives 8,643 contracted buses: 2,445 single deck and 6,198 double deck; 950 battery electric and 20 hydrogen. The audit includes registration-year cohorts, making fleet-age modeling stronger than Vancouver's publicly confirmed register. It does not itself provide route blocks, depot interconnections or charging electricity prices. The operator-contract structure requires treating TfL payments and operators' resource costs separately. Hydrogen vehicles cannot count toward the strict electric endpoint.

## Why Vancouver remains the first case

Official 2023 route-level service, time-bin frequency and direction-load CSVs give unusually usable service calibration and a 98.0% statutory service-hour cross-check. TfL has the stronger published age register. If exact TransLink vehicle blocks and 2023 class/age register cannot be obtained, TfL is the better candidate for *age-cohort* analysis, while no case can claim fully verified service preservation from aggregate public data alone.
