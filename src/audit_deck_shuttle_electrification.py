"""Audit electric double-deck and community-shuttle feasibility evidence.

This module is deliberately separate from the city-wide transition model.  It
does not overwrite or reinterpret the latter's existing 2033 result.  Instead,
it screens the 2023 weekday cap85/cap24 block proxies, records the published
cost and technology evidence, and prints class-specific low/central/high
envelopes together with their time-of-knowledge labels.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"

BLOCKS_FILE = PROC / "vancouver_blocks_weekday_2023.csv"
RANGE_AUDIT_FILE = RESULTS / "vancouver_block_range_audit.json"
FLEET_BRIDGE_FILE = PROC / "translink_fleet_bridge_2023_2025.csv"

ANNUAL_2023_SERVICE_KM = 106_868_324.0
ANNUAL_2023_SHUTTLE_KM = 10_920_849.0 + 2_732_670.0
ANNUAL_2023_SHUTTLE_HOURS = 576_937.0 + 128_684.0
CAD_PER_USD_2024 = 1.37
CAD_PER_USD_2023 = 1.35
CHARGE_EFFICIENCY = 0.90


SOURCES = {
    "translink_tech_2023": {
        "title": "TransLink Mayors' Council technology update, June 2023",
        "url": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf",
    },
    "translink_board_2023": {
        "title": "TransLink public Board meeting package, 22 June 2023",
        "url": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/board-of-directors/board-minutes-and-reports/2023/june/23-06-22-public-board-meeting-package---for-posting.pdf",
    },
    "translink_fleet_2020": {
        "title": "TransLink Low Carbon Fleet Transition Plan, February 2020",
        "url": "https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf",
    },
    "translink_playbook_2024": {
        "title": "TransLink Zero-Emission Fleet Transition Plan summary, November 2024",
        "url": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf",
    },
    "translink_budget_2025": {
        "title": "TransLink 2025 Business Plan",
        "url": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf",
    },
    "translink_cmbc_fleet": {
        "title": "Coast Mountain Bus Company fleet page",
        "url": "https://www.translink.ca/about%20us/about%20translink/operating%20companies/coast%20mountain%20bus%20company",
    },
    "translink_cmbc_2025_snapshot": {
        "title": "CMBC active and in-storage fleet snapshot, 18 November 2025",
        "url": "https://www.translink.ca/-/media/translink/documents/about-translink/freedom-of-information/cmbc-fleet--active--instorage.pdf",
    },
    "translink_deck_2017": {
        "title": "TransLink launches double-decker bus pilot project",
        "url": "https://www.translink.ca/news/2017/november/translink%20launches%20double%20decker%20bus%20pilot%20project",
    },
    "translink_deck_2019": {
        "title": "Double-decker buses rolling into service this October",
        "url": "https://www.translink.ca/news/2019/august/double-decker%20buses%20rolling%20into%20service%20this%20october",
    },
    "translink_buzzer_2019": {
        "title": "PNE Fair: Double the delight with our double-decker bus onsite",
        "url": "https://buzzer.translink.ca/2019/08/pne-fair-double-the-delight-with-our-double-decker-bus-onsite/",
    },
    "translink_30ft_2025": {
        "title": "TransLink tests a 30-foot battery-electric bus",
        "url": "https://buzzer.translink.ca/2025/03/were-testing-a-30-foot-battery-electric-bus/",
    },
    "translink_events": {
        "title": "TransLink planned special events: vehicle capacities",
        "url": "https://www.translink.ca/about-us/doing-business-with-translink/planned-special-events",
    },
    "gtfs_2023": {
        "title": "TransLink fall-2023 GTFS, immutable public mirror commit eb584b1",
        "url": "https://github.com/JaydenCWong/JAAM-project/tree/eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b/backend/engine/translink_data",
    },
    "adl_hk_spec_2023": {
        "title": "Alexander Dennis Enviro500EV Hong Kong specification, 2023",
        "url": "https://www.alexander-dennis.com/site-content/uploads/2023/10/Enviro500EV-Hong-Kong-2023-11.pdf",
    },
    "adl_kmb_launch_2024": {
        "title": "KMB launches Enviro500EV passenger service, May 2024",
        "url": "https://www.alexander-dennis.com/kmb-launches-alexander-dennis-enviro500ev-into-hong-kong-service-following-completion-of-testing-and-certification/",
    },
    "adl_na_2021": {
        "title": "Alexander Dennis unveils the Enviro500EV CHARGE for North America",
        "url": "https://www.alexander-dennis.com/alexander-dennis-unveils-its-first-zero-emission-three-axle-double-deck-bus-the-enviro500ev-charge-for-north-america/",
    },
    "adl_na_current": {
        "title": "Alexander Dennis North America Enviro500EV product page",
        "url": "https://www.alexander-dennis.com/buses/enviro500ev-north-america/",
    },
    "foothill_2024": {
        "title": "Foothill Transit Executive Board agenda, 26 January 2024",
        "url": "https://www.foothilltransit.org/sites/default/files/2024-01/01-26-24_eb_agenda_packet.pdf",
    },
    "sound_2024": {
        "title": "InductEV: Sound Transit wireless charging for 48 electric buses",
        "url": "https://www.prnewswire.com/news-releases/sound-transit-to-go-wireless-in-seattle-with-48-electric-buses-including-33-double-deckers-302066915.html",
    },
    "endera_2023": {
        "title": "Endera 2023 all-electric shuttle announcement",
        "url": "https://www.enderamotors.com/press-releases/endera-unveils-the-2023-all-electric-shuttle-model-with-extended-range-and-fast-charging-speeds",
    },
    "endera_calact_2023": {
        "title": "Endera CALACT contract announcement",
        "url": "https://www.enderamotors.com/blog/press-releases/endera-selected-for-largest-state-ev-bus-contract-in-us-history/",
    },
    "greenpower_evstar": {
        "title": "GreenPower EV Star Passenger Van product page",
        "url": "https://greenpowermotor.com/gp-products/ev-star/",
    },
    "greenpower_ev250": {
        "title": "GreenPower EV250 Bus product page",
        "url": "https://greenpowermotor.com/gp-products/ev250-bus/",
    },
    "greenpower_sacrt": {
        "title": "GreenPower delivery of EV Stars to Sacramento Regional Transit",
        "url": "https://greenpowermotor.com/greenpower-delivery-ev-stars-sacrt/",
    },
    "greenpower_grant": {
        "title": "Grant Transit Authority orders four wirelessly charged EV Stars",
        "url": "https://greenpowermotor.com/wireless-buy-america-compliant-ev-stars-grant-transit-authority/",
    },
    "lion_2023": {
        "title": "Lion Electric fourth-quarter and fiscal 2023 results",
        "url": "https://www.prnewswire.com/news-releases/lion-electric-announces-fourth-quarter-and-fiscal-2023-results-302075488.html",
    },
    "avta_2020": {
        "title": "Antelope Valley Transit Authority Board agenda, 25 February 2020",
        "url": "https://www.avta.com/downloads/meetings/bod/2020/022520-agenda.pdf",
    },
    "vicinity_2021": {
        "title": "Vicinity Motor Corp. C$6 million initial order from Calgary Transit",
        "url": "https://www.sec.gov/Archives/edgar/data/1834975/000173112222000597/e3635_ex99-1.htm",
    },
    "calgary_current": {
        "title": "Calgary Transit electric shuttle bus pilot project update",
        "url": "https://www.calgarytransit.com/plans---projects/electric-bus-pilot-project.html",
    },
    "redwood_2023": {
        "title": "Redwood Coast Transit Authority Board packet, April 2023",
        "url": "https://redwoodcoasttransit.org/wp-content/uploads/2023/04/RCTA-Agenda-Packet-4-24-2023.pdf",
    },
    "newflyer_2023_brochure": {
        "title": "New Flyer Xcelsior CHARGE NG brochure, January 2023",
        "url": "https://www.newflyer.com/site-content/uploads/2023/01/Xcelsior-CHARGE_NG_Brochure.pdf",
    },
    "bc_suvi_2021": {
        "title": "BC Specialty-Use Vehicle Incentive Program eligible-vehicle list, 2 September 2021",
        "url": "https://pluginbc.ca/wp/wp-content/uploads/2020/12/SUVI_MHD_03_09_2021.pdf",
    },
}


def parameter_row(
    parameter_id: str,
    asset_class: str,
    parameter: str,
    value: str | float | int,
    unit: str,
    currency: str,
    source_year: int | str,
    availability_2023: str,
    source_id: str,
    page: str,
    status: str,
    scope: str,
) -> dict:
    source = SOURCES[source_id]
    return {
        "parameter_id": parameter_id,
        "asset_class": asset_class,
        "parameter": parameter,
        "value": value,
        "unit": unit,
        "currency": currency or "not applicable",
        "source_year": source_year,
        "availability_at_2023_decision": availability_2023,
        "status": status,
        "source_title": source["title"],
        "source_page": page,
        "source_url": source["url"],
        "scope": scope,
    }


PARAMETERS = [
    parameter_row("D01", "double_deck", "TransLink double-decker fleet", 57,
                  "vehicles", "", "2019 planned; 2023 procurement tracker",
                  "KNOWN: 32 base-order and 25 option vehicles", "translink_deck_2019",
                  "web release, unpaginated; 25-bus total also at Buzzer 2019 web post",
                  "DERIVED_FROM_TWO_OFFICIAL_QUANTITIES",
                  "32 + 25 = 57; the GTFS has 57 cap85 duties, but neither source identifies vehicle-to-block assignment"),
    parameter_row("D02", "double_deck", "25 double-deckers accepted by Q2 2023", 25,
                  "vehicles", "", 2023, "KNOWN", "translink_board_2023", "22",
                  "OBSERVED_PROCUREMENT_STATE", "Fleet procurement 2023-2024 table; acceptance is not an as-operated roster"),
    parameter_row("D03", "double_deck", "2023 weekday cap85 duty-block proxy", 57,
                  "blocks/day", "", 2023, "DERIVED FROM KNOWN GTFS", "gtfs_2023",
                  "GTFS files, computed; see src/analyze_vancouver_blocks.py",
                  "DERIVED_ROUTE_CAPACITY_PROXY", "The route-level 85-passenger signature supports a deck proxy; it is not a vehicle ID field"),
    parameter_row("D04", "double_deck", "Seats on TransLink's Enviro500 pilot", "80-86",
                  "seats/vehicle", "", 2017, "KNOWN", "translink_deck_2017",
                  "web release, unpaginated", "OBSERVED", "In service TransLink specification; compare with the 85-space 2023 capacity proxy"),
    parameter_row("D05", "double_deck", "2023 Enviro500EV battery-system energy", 472,
                  "kWh", "", 2023, "KNOWN", "adl_hk_spec_2023", "p. 1", "OBSERVED",
                  "Hong Kong production specification, not a Vancouver winter guarantee"),
    parameter_row("D06", "double_deck", "2023 Enviro500EV maximum DC charge rate", 150,
                  "kW", "", 2023, "KNOWN", "adl_hk_spec_2023", "p. 1", "OBSERVED",
                  "CCS; North American connector and site compatibility require separate checks"),
    parameter_row("D07", "double_deck", "2023 Enviro500EV capacity in KMB specification", 122,
                  "passengers/vehicle", "", 2023, "KNOWN AFTER MAY 2024 ENTRY", "adl_kmb_launch_2024",
                  "web release, unpaginated", "OBSERVED_PRODUCT_CONFIGURATION",
                  "82 seated plus two wheelchair spaces and standees in KMB configuration; TransLink seats are 80-86"),
    parameter_row("D08", "double_deck", "North-American Enviro500EV CHARGE prototype energy", 648,
                  "kWh", "", 2021, "KNOWN", "adl_na_2021", "web release, unpaginated", "OBSERVED",
                  "45-ft, up to 82 seats, heat pump; prototype facts do not establish 2023 fleet availability"),
    parameter_row("D09", "double_deck", "Next-generation NA Enviro500EV battery", ">700",
                  "kWh", "", 2024, "LATER_THAN_2023", "foothill_2024", "p. 21", "OBSERVED",
                  "Foothill board describes the next-generation configuration ordered in 2024"),
    parameter_row("D10", "double_deck", "Next-generation NA Enviro500EV claimed range/efficiency", "300 mi at 2 kWh/mi",
                  "mi; kWh/mi", "", 2024, "LATER_THAN_2023", "foothill_2024", "p. 21", "PROCUREMENT_CLAIM",
                  "Mild-condition planning figure represented in the Board report; not winter-certified"),
    parameter_row("D11", "double_deck", "Foothill next-generation Enviro500EV contract", 21_096_000,
                  "USD/12 buses", "USD", 2024, "LATER_THAN_2023", "foothill_2024", "p. 21", "OBSERVED_CONTRACT",
                  "USD 1,758,000 per 42-ft bus; excludes charging infrastructure and taxes"),
    parameter_row("D12", "double_deck", "Current NA Enviro500EV configurable battery/top range", "709 or 827; 340 mi; 300 kW",
                  "kWh; mi; kW", "", "current 2026", "LATER_THAN_2023", "adl_na_current",
                  "web specification, unpaginated", "OBSERVED_LATER_PRODUCT", "Used only as an optimistic 2033 technology envelope"),
    parameter_row("D13", "double_deck", "2023 TransLink generic BEB screening price", 1_200_000,
                  "CAD/vehicle", "CAD", 2023, "KNOWN", "translink_tech_2023", "p. 29", "PLANNING_SCREEN",
                  "Not deck-specific; retained only as a lower bound"),
    parameter_row("D14", "double_deck", "2023 one in-route charger equipment screen", "460,000-610,000",
                  "CAD/charger", "CAD", 2023, "KNOWN", "translink_tech_2023", "p. 29", "PLANNING_SCREEN",
                  "Equipment-oriented screening range; site and utility scope differs"),
    parameter_row("D15", "double_deck", "In-route charger fully burdened cost", "900,000-1,200,000; average 1,000,000; p85 1,300,000",
                  "CAD/charger", "CAD", 2019, "KNOWN", "translink_fleet_2020", "pp. 97-98", "ENGINEERING_ESTIMATE",
                  "Power module, pantograph, customer-side distribution and site works; excludes some project delivery costs"),
    parameter_row("D16", "double_deck", "In-route charger provisioning", "1 per ~7 peak buses; 300-450 kW; 5-15 min/event; 45-90 min/day",
                  "chargers, kW, minutes", "", 2019, "KNOWN", "translink_fleet_2020", "p. 64", "ENGINEERING_ESTIMATE",
                  "CMBC 40/60-ft planning rule, not a 57-bus deck schedule"),
    parameter_row("D17", "double_deck", "Marpole depot envelope", "500,000,000 / 340",
                  "CAD/bus position", "CAD", 2023, "KNOWN SCREEN, LATER COMMISSIONING", "translink_tech_2023",
                  "p. 30", "PLANNING_SCREEN", "Includes facility scope and is not a charger-only unit price"),
    parameter_row("D18", "double_deck", "Port Coquitlam charger program envelope", "46,000,000 / 10",
                  "CAD/charger", "CAD", 2023, "KNOWN SCREEN", "translink_tech_2023", "p. 30", "PLANNING_SCREEN",
                  "High site-integration envelope; not the equipment price"),
    parameter_row("D19", "double_deck", "Hamilton Route-100 charging envelope", 2_300_000,
                  "CAD / 19 planned BEBs", "CAD", 2023, "KNOWN SCREEN", "translink_tech_2023", "p. 30", "PLANNING_SCREEN",
                  "Plug-in depot chargers plus one in-route charger; after removing the 610k in-route equipment screen, /19 gives about CAD 89k per vehicle as a depot-share sensitivity"),
    parameter_row("D20", "double_deck", "BC incentive-list double-deck EV MSRPs", "DD8: USD 870,000; DD10: USD 1,165,000",
                  "USD/vehicle", "USD", "2020 model year; list dated 2021", "KNOWN", "bc_suvi_2021", "p. 1", "PUBLIC_LIST_PRICE",
                  "BYD double-deck coach configurations; not a TransLink bid, winter package or three-axle transit homologation"),
    parameter_row("S01", "community_shuttle", "Detailed pre-bridge shuttle stock", 206,
                  "vehicles", "", "Nov 2021 / 2022 bridge", "KNOWN HISTORICAL; 2023 REGISTER MISSING", "translink_cmbc_fleet",
                  "web fleet table, unpaginated; 163 CMBC + 43 contracted", "OBSERVED_DATED_SNAPSHOT",
                  "Use as upper population anchor, not a 2023 roster"),
    parameter_row("S02", "community_shuttle", "Active gasoline shuttle stock", 171,
                  "vehicles", "", 2025, "LATER_THAN_2023", "translink_cmbc_2025_snapshot", "p. 1 summary table",
                  "OBSERVED_RETROSPECTIVE", "18 November 2025 active/in-storage snapshot; 63 other vehicles are separately reported in storage"),
    parameter_row("S03", "community_shuttle", "Community Shuttle order in June 2023 procurement tracker", 168,
                  "vehicles ordered", "", 2023, "KNOWN", "translink_board_2023", "p. 22", "OBSERVED_PROCUREMENT_STATE",
                  "Order quantity, zero accepted at the snapshot, deliveries Q4 2023-Q1 2025; not fleet stock or EV commitment"),
    parameter_row("S04", "community_shuttle", "2020 fleet-plan shuttle stock", 200,
                  "26-ft gasoline vehicles", "", 2020, "KNOWN HISTORICAL", "translink_fleet_2020", "p. 16",
                  "OBSERVED_HISTORICAL", "Includes 89 contracted shuttles; five-year retirement policy stated in source"),
    parameter_row("S05", "community_shuttle", "2023 shuttle service", "10,920,849 CMBC + 2,732,670 contracted",
                  "service-km", "", "2023 actual reported 2025", "2023 OBSERVED; REPORT LATER", "translink_budget_2025",
                  "p. 23", "OBSERVED_RETROSPECTIVE", "Sum used for energy intensity; includes West Vancouver and contract shuttles"),
    parameter_row("S06", "community_shuttle", "2023 shuttle service hours", "576,937 CMBC + 128,684 contracted",
                  "service-hours", "", "2023 actual reported 2025", "2023 OBSERVED; REPORT LATER", "translink_budget_2025",
                  "p. 23", "OBSERVED_RETROSPECTIVE", "Sum equals approximately the independent 706,000-hour statutory round"),
    parameter_row("S07", "community_shuttle", "2023 weekday cap24 duty-block proxy", 101,
                  "blocks/day", "", 2023, "DERIVED FROM KNOWN GTFS", "gtfs_2023",
                  "GTFS files, computed; see src/analyze_vancouver_blocks.py",
                  "DERIVED_ROUTE_CAPACITY_PROXY", "Not the 171-206 vehicle stock and not a complete shuttle route roster"),
    parameter_row("S08", "community_shuttle", "Current TransLink community-shuttle load limit", 20,
                  "passengers/vehicle", "", 2026, "LATER POLICY; compare 24 historical planning value", "translink_events",
                  "web capacity table, unpaginated", "CURRENT_OPERATING_LIMIT", "Do not use as proof of the 2023 legal or operating limit"),
    parameter_row("S09", "community_shuttle", "GreenPower EV Star capacity/energy/range/charge", "19 + driver; 118 kWh; 150 mi; 60 kW",
                  "passengers; kWh; mi; kW", "", "product introduced before 2023; page current", "KNOWN PRODUCT; CURRENT PAGE NOT A 2023 SNAPSHOT",
                  "greenpower_evstar", "web specification, unpaginated", "OBSERVED_PRODUCT_SPECIFICATION",
                  "19 passengers plus driver corresponds to TransLink's 20-space limit in this configuration"),
    parameter_row("S10", "community_shuttle", "Endera 2023 shuttle battery/charging", "150 kWh; 10-80% in 30 min",
                  "kWh; minutes", "", 2023, "KNOWN", "endera_2023", "web release, unpaginated", "OBSERVED_PRODUCT_SPECIFICATION",
                  "Announced 28 March 2023; initial delivery Q3 2023, not a Vancouver operational record"),
    parameter_row("S11", "community_shuttle", "Endera 2023 B-Series seating", "12+2 or 16+2",
                  "seats + wheelchair positions", "", 2023, "KNOWN", "endera_calact_2023", "web release, unpaginated",
                  "OBSERVED_PRODUCT_SPECIFICATION", "16+2 is below a 20-passenger duty; one-for-one capacity may require extra departures"),
    parameter_row("S12", "community_shuttle", "LionM nominal battery/range", "160 kWh; 150 mi",
                  "kWh; mi", "", 2018-2023, "KNOWN PRODUCT, NOT COMMERCIALLY AVAILABLE", "lion_2023",
                  "fiscal 2023 release, unpaginated", "COMPANY_DISCLOSURE", "Lion indefinitely delayed commercial LionM production in Q4 2023"),
    parameter_row("S13", "community_shuttle", "Calgary Transit electric-shuttle order", 6_000_000,
                  "CAD/14 vehicles", "CAD", 2021, "KNOWN CONTRACT, NOT DELIVERY", "vicinity_2021",
                  "SEC exhibit, unpaginated", "OBSERVED_CONTRACT", "Derived C$428,571 per 28-ft/22-passenger vehicle; order later cancelled"),
    parameter_row("S14", "community_shuttle", "Calgary pilot outcome", "contract ended; C$5 million spent; mostly charging infrastructure",
                  "CAD; project status", "CAD", 2024, "LATER_THAN_2023", "calgary_current", "web update, unpaginated",
                  "RETROSPECTIVE_OPERATOR_STATEMENT", "Vendor could not meet delivery commitments; charging equipment remains multifunctional"),
    parameter_row("S15", "community_shuttle", "AVTA six-EV-Star transaction", 574_683,
                  "USD/6 vehicles", "USD", 2020, "KNOWN", "avta_2020", "pp. 2 and 162", "OBSERVED_PUBLIC_CONTRACT_SCREEN",
                  "USD 95,781 per vehicle in the Board action; source states a USD 100,000/vehicle HVIP credit is included in the purchase price"),
    parameter_row("S16", "community_shuttle", "AVTA six depot chargers", 183_948,
                  "USD/6 chargers", "USD", 2020, "KNOWN", "avta_2020", "pp. 2 and 164", "OBSERVED_PUBLIC_CONTRACT_SCREEN",
                  "USD 30,658 per charger equipment; installation and utility upgrade are not established by the line item"),
    parameter_row("S17", "community_shuttle", "Redwood Coast 2023 EV Star grant", 160_000,
                  "USD/one bus", "USD", 2023, "KNOWN", "redwood_2023", "p. 5", "OBSERVED_GRANT_CURRENT_AT_2023",
                  "Grant covers most, not all, of one EV Star Plus excluding charger; therefore a gross approximation near USD 200,000 is more defensible than USD 160,000 as vehicle price"),
    parameter_row("S18", "community_shuttle", "2025 30-ft TransLink trial vehicle", "22 seats; 44 max; about 250 km",
                  "passengers; range-km", "", 2025, "LATER_THAN_2023", "translink_30ft_2025", "web article, unpaginated",
                  "LATER_OPERATOR_TEST", "Letenda Electrip; rear-axle steering tested for narrow routes; no delivered fleet outcome"),
    parameter_row("S19", "community_shuttle", "BC incentive-list small EV prices", "EV Star Min-e Bus with side USD 195,500; Transit Plus USD 239,500; Transit Plus with ADA USD 265,000",
                  "USD/vehicle", "USD", "2021 model year; list dated 2021", "KNOWN", "bc_suvi_2021", "pp. 1-2", "PUBLIC_LIST_PRICE",
                  "Base MSRP before the listed incentive; use the ADA configuration when preserving accessibility"),
    parameter_row("S20", "community_shuttle", "BC incentive-list comparable 25-28 ft EVs", "Vicinity Lightning 168 kWh USD 400,000; LionM 160 kWh USD 395,000",
                  "USD/vehicle", "USD", "2021 model year; list dated 2021", "KNOWN", "bc_suvi_2021", "p. 3", "PUBLIC_LIST_PRICE",
                  "Useful triangulation for the Calgary contract; a list price is not delivery performance"),
    parameter_row("G01", "policy", "2024 TransLink double-deck recommendation", "begin transition after 2030",
                  "planning statement", "", 2024, "LATER_THAN_2023", "translink_playbook_2024", "p. 20", "OPERATOR_PLAN",
                  "Recommendation 7; no full-electric deck commitment before that date in this plan"),
    parameter_row("G02", "policy", "2024 TransLink community-shuttle recommendation", "not currently feasible for most blocks; begin mid-2030s",
                  "planning statement", "", 2024, "LATER_THAN_2023", "translink_playbook_2024", "p. 20", "OPERATOR_PLAN",
                  "Recommendation 8; explicitly conflicts with a 2033 all-shuttle claim"),
    parameter_row("G03", "product_market", "New Flyer Xcelsior CHARGE NG size family", "35/40/60 ft",
                  "vehicle family", "", 2023, "KNOWN", "newflyer_2023_brochure", "pp. 1, 5-6", "PRODUCT_LINE_AUDIT",
                  "No direct 20-passenger shuttle or three-axle double-decker; rapid charging and 40-ft capacity are cross-checks, not homologated Vancouver vehicle evidence"),
]


SCENARIOS = {
    "low": {
        "label": "2023-known / lower-capability envelope",
        "double_deck": {
            "battery_kwh": 472.0,
            "usable_fraction": 0.80,
            "winter_kwh_per_km": 1.79,
            "charge_power_kw": 150.0,
            "fleet_low": 57,
            "fleet_high": 57,
            "unit_cost_cad_low": 1_165_000.0 * CAD_PER_USD_2023,
            "unit_cost_cad_high": 1_165_000.0 * CAD_PER_USD_2023,
            "depot_share_cad_per_vehicle": (2_300_000.0 - 610_000.0) / 19,
            "chargers": 9,
            "charger_cost_cad_each": 610_000.0,
            "unit_cost_basis": "2021 BC incentive list: BYD DD10 double-deck coach MSRP US$1.165m at assumed CAD/USD 1.35; no TransLink bid",
        },
        "community_shuttle": {
            "battery_kwh": 118.0,
            "usable_fraction": 0.80,
            "winter_kwh_per_km": 0.80,
            "charge_power_kw": 60.0,
            "fleet_low": 171,
            "fleet_high": 171,
            "unit_cost_cad_low": 265_000.0 * CAD_PER_USD_2023,
            "unit_cost_cad_high": 265_000.0 * CAD_PER_USD_2023,
            "vehicles_per_charger": 3,
            "charger_cost_cad_each": 50_000.0,
            "unit_cost_basis": "2021 BC incentive list: EV Star Transit Plus with ADA MSRP US$265k at assumed CAD/USD 1.35",
        },
    },
    "central": {
        "label": "observed production / operational central envelope",
        "double_deck": {
            "battery_kwh": 700.0,
            "usable_fraction": 0.85,
            "winter_kwh_per_km": 1.80,
            "charge_power_kw": 300.0,
            "fleet_low": 57,
            "fleet_high": 57,
            "unit_cost_cad_low": 21_096_000.0 / 12 * CAD_PER_USD_2024,
            "unit_cost_cad_high": 21_096_000.0 / 12 * CAD_PER_USD_2024,
            "depot_share_cad_per_vehicle": (2_300_000.0 - 610_000.0) / 19,
            "chargers": 9,
            "charger_cost_cad_each": 1_300_000.0,
            "unit_cost_basis": "Foothill 2024 contract: US$1.758m/bus at assumed CAD/USD 1.37",
        },
        "community_shuttle": {
            "battery_kwh": 150.0,
            "usable_fraction": 0.85,
            "winter_kwh_per_km": 0.90,
            "charge_power_kw": 70.0,
            "fleet_low": 189,
            "fleet_high": 189,
            "unit_cost_cad_low": 6_000_000.0 / 14,
            "unit_cost_cad_high": 6_000_000.0 / 14,
            "vehicles_per_charger": 2,
            "charger_cost_cad_each": 100_000.0,
            "unit_cost_basis": "Calgary June-2021 order: over C$6m for 14 vehicles; midpoint fleet 189 of 171-206",
        },
    },
    "high": {
        "label": "2033 forward / high-capability and high-cost envelope",
        "double_deck": {
            "battery_kwh": 827.0,
            "usable_fraction": 0.90,
            "winter_kwh_per_km": 1.60,
            "charge_power_kw": 300.0,
            "fleet_low": 57,
            "fleet_high": 57,
            "unit_cost_cad_low": 21_096_000.0 / 12 * CAD_PER_USD_2024 * 1.25,
            "unit_cost_cad_high": 21_096_000.0 / 12 * CAD_PER_USD_2024 * 1.25,
            "depot_share_cad_per_vehicle": 500_000_000.0 / 340,
            "chargers": 9,
            "charger_cost_cad_each": 46_000_000.0 / 10,
            "unit_cost_basis": "2024 Foothill actual converted to CAD plus a 25% uncertainty/supply premium",
        },
        "community_shuttle": {
            "battery_kwh": 260.0,
            "usable_fraction": 0.85,
            "winter_kwh_per_km": 0.90,
            "charge_power_kw": 120.0,
            "fleet_low": 206,
            "fleet_high": 206,
            "unit_cost_cad_low": 650_000.0,
            "unit_cost_cad_high": 650_000.0,
            "vehicles_per_charger": 1,
            "charger_cost_cad_each": 300_000.0,
            "unit_cost_basis": "Forward 30-ft/20+ capacity vehicle and site-integration planning assumption; Calgary charging spend is the upper anchor",
        },
    },
}


def scenario_range_km(parameters: dict) -> float:
    return (
        parameters["battery_kwh"] * parameters["usable_fraction"]
        / parameters["winter_kwh_per_km"]
    )


def select_duty_blocks(blocks: pd.DataFrame, proxy_class: str, expected: int) -> pd.DataFrame:
    selected = blocks.loc[blocks["block_proxy_class"].eq(proxy_class)].copy()
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} {proxy_class} blocks, found {len(selected)}")
    for column in ("distance_lower_km", "distance_upper_km", "scheduled_hours", "span_hours"):
        selected[column] = pd.to_numeric(selected[column], errors="raise")
    return selected


def screen_duties(blocks: pd.DataFrame, asset_class: str, scenario: str, parameters: dict) -> pd.DataFrame:
    frame = blocks.copy()
    planned_range = scenario_range_km(parameters)
    frame["asset_class"] = asset_class
    frame["scenario"] = scenario
    frame["planned_range_km"] = planned_range
    frame["overnight_status"] = "CERTAIN_FEASIBLE"
    uncertain = frame["distance_upper_km"].gt(planned_range) & frame["distance_lower_km"].le(planned_range)
    infeasible = frame["distance_lower_km"].gt(planned_range)
    frame.loc[uncertain, "overnight_status"] = "INTERVAL_STRADDLES"
    frame.loc[infeasible, "overnight_status"] = "CERTAIN_SHORTFALL"
    frame["shortfall_lower_km"] = (frame["distance_lower_km"] - planned_range).clip(lower=0)
    frame["shortfall_upper_km"] = (frame["distance_upper_km"] - planned_range).clip(lower=0)
    frame["shortfall_energy_lower_kwh"] = frame["shortfall_lower_km"] * parameters["winter_kwh_per_km"]
    frame["shortfall_energy_upper_kwh"] = frame["shortfall_upper_km"] * parameters["winter_kwh_per_km"]
    usable_charge_kw = parameters["charge_power_kw"] * CHARGE_EFFICIENCY
    frame["charge_minutes_lower"] = 60 * frame["shortfall_energy_lower_kwh"] / usable_charge_kw
    frame["charge_minutes_upper"] = 60 * frame["shortfall_energy_upper_kwh"] / usable_charge_kw
    frame["duty_energy_lower_kwh"] = frame["distance_lower_km"] * parameters["winter_kwh_per_km"]
    frame["duty_energy_upper_kwh"] = frame["distance_upper_km"] * parameters["winter_kwh_per_km"]
    return frame


def scenario_summary(screen: pd.DataFrame, asset_class: str, scenario: str, parameters: dict) -> dict:
    status = screen["overnight_status"].value_counts()
    certain_shortfall = screen[screen["overnight_status"].eq("CERTAIN_SHORTFALL")]
    fleet_low = int(parameters["fleet_low"])
    fleet_high = int(parameters["fleet_high"])
    unit_low = float(parameters["unit_cost_cad_low"])
    unit_high = float(parameters["unit_cost_cad_high"])
    vehicle_low = fleet_low * unit_low
    vehicle_high = fleet_high * unit_high

    if asset_class == "double_deck":
        charger_count_low = charger_count_high = int(parameters["chargers"])
        depot_low = fleet_low * float(parameters["depot_share_cad_per_vehicle"])
        depot_high = fleet_high * float(parameters["depot_share_cad_per_vehicle"])
    else:
        charger_count_low = math.ceil(fleet_low / int(parameters["vehicles_per_charger"]))
        charger_count_high = math.ceil(fleet_high / int(parameters["vehicles_per_charger"]))
        depot_low = depot_high = 0.0

    charger_unit = float(parameters["charger_cost_cad_each"])
    infrastructure_low = depot_low + charger_count_low * charger_unit
    infrastructure_high = depot_high + charger_count_high * charger_unit
    annual_km_low = float(parameters.get("annual_km_low", 0.0))
    annual_km_high = float(parameters.get("annual_km_high", 0.0))

    return {
        "asset_class": asset_class,
        "scenario": scenario,
        "label": SCENARIOS[scenario]["label"],
        "duty_blocks_screened": int(len(screen)),
        "battery_kwh": float(parameters["battery_kwh"]),
        "usable_fraction": float(parameters["usable_fraction"]),
        "winter_kwh_per_km": float(parameters["winter_kwh_per_km"]),
        "charge_power_kw": float(parameters["charge_power_kw"]),
        "planned_range_km": scenario_range_km(parameters),
        "overnight_feasible_certain_blocks": int(status.get("CERTAIN_FEASIBLE", 0)),
        "overnight_range_interval_blocks": int(status.get("INTERVAL_STRADDLES", 0)),
        "overnight_certain_shortfall_blocks": int(status.get("CERTAIN_SHORTFALL", 0)),
        "overnight_feasible_possible_blocks": int(status.get("CERTAIN_FEASIBLE", 0) + status.get("INTERVAL_STRADDLES", 0)),
        "total_duty_energy_lower_kwh": float(screen["duty_energy_lower_kwh"].sum()),
        "total_duty_energy_upper_kwh": float(screen["duty_energy_upper_kwh"].sum()),
        "total_shortfall_energy_lower_kwh": float(screen["shortfall_energy_lower_kwh"].sum()),
        "total_shortfall_energy_upper_kwh": float(screen["shortfall_energy_upper_kwh"].sum()),
        "total_shortfall_charge_minutes_lower": float(screen["charge_minutes_lower"].sum()),
        "total_shortfall_charge_minutes_upper": float(screen["charge_minutes_upper"].sum()),
        "mean_charge_minutes_per_certain_shortfall_upper": (
            float(certain_shortfall["charge_minutes_upper"].mean())
            if len(certain_shortfall) else 0.0
        ),
        "annual_class_km_low": annual_km_low,
        "annual_class_km_high": annual_km_high,
        "annual_energy_low_kwh": annual_km_low * float(parameters["winter_kwh_per_km"]),
        "annual_energy_high_kwh": annual_km_high * float(parameters["winter_kwh_per_km"]),
        "fleet_low": fleet_low,
        "fleet_high": fleet_high,
        "vehicle_unit_cost_cad_low": unit_low,
        "vehicle_unit_cost_cad_high": unit_high,
        "vehicle_cost_cad_low": vehicle_low,
        "vehicle_cost_cad_high": vehicle_high,
        "charger_count_low": charger_count_low,
        "charger_count_high": charger_count_high,
        "charger_cost_cad_each": charger_unit,
        "infrastructure_cost_cad_low": infrastructure_low,
        "infrastructure_cost_cad_high": infrastructure_high,
        "capital_cost_cad_low": vehicle_low + infrastructure_low,
        "capital_cost_cad_high": vehicle_high + infrastructure_high,
        "unit_cost_basis": parameters["unit_cost_basis"],
        "cost_boundary": "nominal vehicle + incremental charging/site envelope; excludes operations, energy, taxes, financing and residual value",
    }


def main() -> None:
    blocks = pd.read_csv(BLOCKS_FILE, dtype={"block_id": str, "route_id": str, "highest_class_route": str})
    deck = select_duty_blocks(blocks, "cap85", 57)
    shuttle = select_duty_blocks(blocks, "cap24", 101)

    range_audit = json.loads(RANGE_AUDIT_FILE.read_text(encoding="utf-8"))
    weekday = next(day for day in range_audit["days"] if day["kind"] == "weekday")
    weekday_lower_km = float(weekday["distance_lower_km"])
    weekday_upper_km = float(weekday["distance_upper_km"])
    deck_annual_share_low = float(deck["distance_lower_km"].sum()) / weekday_lower_km
    deck_annual_share_high = float(deck["distance_upper_km"].sum()) / weekday_upper_km
    deck_annual_km_low = ANNUAL_2023_SERVICE_KM * deck_annual_share_low
    deck_annual_km_high = ANNUAL_2023_SERVICE_KM * deck_annual_share_high

    fleet_bridge = pd.read_csv(FLEET_BRIDGE_FILE)
    snapshot_2025 = fleet_bridge[fleet_bridge["snapshot"].eq(2025)]
    shuttle_2025 = int(snapshot_2025.loc[snapshot_2025["metric"].eq("gasoline_shuttle"), "value"].iloc[0])
    if shuttle_2025 != 171:
        raise ValueError(f"Expected 171 gasoline shuttles in 2025 snapshot, found {shuttle_2025}")
    if not (shuttle["distance_upper_km"] > 0).all() or not (deck["distance_upper_km"] > 0).all():
        raise ValueError("Duty distances must be positive")

    scenario_rows = []
    screens = []
    for scenario_name, scenario in SCENARIOS.items():
        deck_parameters = dict(scenario["double_deck"])
        deck_parameters.update({"annual_km_low": deck_annual_km_low, "annual_km_high": deck_annual_km_high})
        deck_screen = screen_duties(deck, "double_deck", scenario_name, deck_parameters)
        screens.append(deck_screen)
        scenario_rows.append(scenario_summary(deck_screen, "double_deck", scenario_name, deck_parameters))

        shuttle_parameters = dict(scenario["community_shuttle"])
        shuttle_parameters.update({"annual_km_low": ANNUAL_2023_SHUTTLE_KM, "annual_km_high": ANNUAL_2023_SHUTTLE_KM})
        shuttle_screen = screen_duties(shuttle, "community_shuttle", scenario_name, shuttle_parameters)
        screens.append(shuttle_screen)
        scenario_rows.append(scenario_summary(shuttle_screen, "community_shuttle", scenario_name, shuttle_parameters))

    duty_screen = pd.concat(screens, ignore_index=True)
    duty_screen = duty_screen.sort_values(["asset_class", "scenario", "block_id"]).reset_index(drop=True)
    scenario_frame = pd.DataFrame(scenario_rows)

    # A compact wide duty table is easier to inspect than 474 long rows, while
    # the JSON retains the full long-form screen for auditability.
    id_columns = [
        "asset_class", "block_id", "highest_class_route", "distance_lower_km",
        "distance_upper_km", "scheduled_hours", "span_hours",
    ]
    wide_parts = []
    for scenario_name in SCENARIOS:
        part = duty_screen[duty_screen["scenario"].eq(scenario_name)].copy()
        columns = {
            "planned_range_km": f"{scenario_name}_range_km",
            "overnight_status": f"{scenario_name}_overnight_status",
            "shortfall_lower_km": f"{scenario_name}_shortfall_lower_km",
            "shortfall_upper_km": f"{scenario_name}_shortfall_upper_km",
            "shortfall_energy_upper_kwh": f"{scenario_name}_shortfall_energy_upper_kwh",
            "charge_minutes_upper": f"{scenario_name}_charge_minutes_upper",
        }
        part = part[id_columns + list(columns)].rename(columns=columns)
        wide_parts.append(part)
    duty_wide = wide_parts[0]
    for part in wide_parts[1:]:
        duty_wide = duty_wide.merge(part, on=id_columns, how="outer", validate="one_to_one")

    fleet_mapping = pd.DataFrame([
        {
            "asset_class": "double_deck",
            "observed_or_derived_units": 57,
            "population_low": 57,
            "population_high": 57,
            "weekday_duty_proxy_blocks": 57,
            "mapping_status": "DERIVED_FLEET_EQUALS_PROXY_COUNT; NOT_VEHICLE_TO_BLOCK_CERTIFIED",
            "mapping_note": "32 ordered in 2019 plus 25 exercised option; 57 cap85 duties in the 2023 fall weekday. Equality is a consistency check, not an ID join.",
        },
        {
            "asset_class": "community_shuttle",
            "observed_or_derived_units": 171,
            "population_low": shuttle_2025,
            "population_high": 206,
            "weekday_duty_proxy_blocks": 101,
            "mapping_status": "CROSS_YEAR_FLEET_INTERVAL; 2023_REGISTER_MISSING",
            "mapping_note": "171 active gasoline shuttles in Nov 2025; 206 detailed stock in the older Nov-2021/2022 bridge (163 CMBC + 43 contracted). The 101 cap24 duties do not equal fleet stock because the GTFS lacks vehicle IDs, garages, propulsion and a complete route-class map.",
        },
    ])
    fleet_mapping["annual_2023_service_km_low"] = [deck_annual_km_low, ANNUAL_2023_SHUTTLE_KM]
    fleet_mapping["annual_2023_service_km_high"] = [deck_annual_km_high, ANNUAL_2023_SHUTTLE_KM]
    fleet_mapping["annual_km_per_physical_vehicle_low"] = [
        deck_annual_km_low / 57,
        ANNUAL_2023_SHUTTLE_KM / 206,
    ]
    fleet_mapping["annual_km_per_physical_vehicle_high"] = [
        deck_annual_km_high / 57,
        ANNUAL_2023_SHUTTLE_KM / 171,
    ]

    parameter_frame = pd.DataFrame(PARAMETERS)
    parameter_frame.to_csv(PROC / "deck_shuttle_parameter_table.csv", index=False, encoding="utf-8")
    fleet_mapping.to_csv(PROC / "deck_shuttle_fleet_mapping.csv", index=False, encoding="utf-8")
    duty_wide.to_csv(PROC / "deck_shuttle_duty_screen_2023.csv", index=False, encoding="utf-8")
    scenario_frame.to_csv(PROC / "deck_shuttle_scenarios.csv", index=False, encoding="utf-8")

    deck_rows = {row["scenario"]: row for row in scenario_rows if row["asset_class"] == "double_deck"}
    shuttle_rows = {row["scenario"]: row for row in scenario_rows if row["asset_class"] == "community_shuttle"}
    report = {
        "status": "CONDITIONAL_TECHNICAL_AND_COST_AUDIT; 2033_FULL_CLASS_FEASIBILITY_UNVERIFIED",
        "scope": "2023 fall weekday cap85 and cap24 duty proxies; TransLink fixed-route service; double-deck and community shuttles only",
        "base_date": "2023-11-14",
        "research_access_date": "2026-10-18",
        "evidence_cutoff_policy": "Every parameter is labelled as known by 2023, derived from 2023, or later. Later product and procurement evidence is never backdated.",
        "parameter_count": len(PARAMETERS),
        "scenario_method": "Planned range = nominal battery x usable fraction / winter kWh-per-km. Duty certainty requires the distance upper bound to be at or below range; a lower bound above range is a certain shortfall. Charging minutes use vehicle charge power x 0.90 efficiency.",
        "source_registry": SOURCES,
        "fleet_mapping": fleet_mapping.to_dict(orient="records"),
        "service_mapping": {
            "total_2023_fixed_route_bus_km": ANNUAL_2023_SERVICE_KM,
            "deck_weekday_distance_share_low": deck_annual_share_low,
            "deck_weekday_distance_share_high": deck_annual_share_high,
            "deck_estimated_annual_km_low": deck_annual_km_low,
            "deck_estimated_annual_km_high": deck_annual_km_high,
            "shuttle_2023_service_km": ANNUAL_2023_SHUTTLE_KM,
            "shuttle_2023_service_hours": ANNUAL_2023_SHUTTLE_HOURS,
            "shuttle_annual_km_per_fleet_vehicle_low": ANNUAL_2023_SHUTTLE_KM / 206,
            "shuttle_annual_km_per_fleet_vehicle_high": ANNUAL_2023_SHUTTLE_KM / 171,
            "shuttle_mean_speed_kmh": ANNUAL_2023_SHUTTLE_KM / ANNUAL_2023_SHUTTLE_HOURS,
        },
        "scenarios": scenario_rows,
        "feasibility_judgment": {
            "double_deck_2033": {
                "verdict": "CONDITIONAL_PHYSICAL_FEASIBILITY_WITH_ENDPOINT_CHARGING; ALL_57_BY_2033_NOT_SUPPORTED_AS_AN_OPERATOR_COMMITMENT",
                "overnight_only": "Fails for the whole 57-block population in every screened scenario. Certain feasible / interval / certain shortfall counts are 33/2/22 at 472 kWh, 35/5/17 at 700 kWh and 43/6/8 at 827 kWh.",
                "charge_requirement": "The fitted range must be complemented by 150-300 kW DC charging or equivalent opportunity charging at terminals. A 2023 150-kW vehicle cannot replicate the 450-kW/5-15-minute strategy published for older 40/60-ft planning without longer dwell or more energy stops.",
                "decision_time_view": "As of 2023, the 472-kWh Enviro500EV specification and a North American prototype existed, but no Vancouver electric deck fleet or winter/payload certification was public. TransLink's later 2024 plan explicitly says to begin deck transition after 2030.",
            },
            "community_shuttle_2033": {
                "verdict": "NOT_ONE_FOR_ONE_WITH_2023_SMALL SHUTTLES; CONDITIONALLY_FEASIBLE_BY_2033_WITH_LARGER_CAPACITY_VEHICLES_AND_CHARGE_STOPS",
                "overnight_only": "Certain feasible / interval / certain shortfall counts are 46/2/53 at 118 kWh, 51/1/49 at 150 kWh and 74/7/20 at 260 kWh. These are all stricter than a claim that most 2023 small-shuttle products cover the day.",
                "capacity": "The 2023 Endera 16+2 layout is short of the 20-space operating limit and can require about 11% more departures/vehicles. The 2025 30-ft Letenda trial has 44-person maximum capacity; it can restore capacity but still needs narrow-street and turning-radius verification.",
                "decision_time_view": "In 2023, small electric shuttle products existed, but the Calgary order for 14 vehicles later failed to deliver and was cancelled. TransLink's 2024 operator plan says community shuttles are not currently feasible for most blocks and should begin in the mid-2030s.",
            },
        },
        "cost_judgment": {
            "double_deck_class_envelope_cad": {
                level: {
                    "capital_low": row["capital_cost_cad_low"],
                    "capital_high": row["capital_cost_cad_high"],
                    "vehicle_unit_basis": row["unit_cost_basis"],
                }
                for level, row in deck_rows.items()
            },
            "community_shuttle_class_envelope_cad": {
                level: {
                    "capital_low": row["capital_cost_cad_low"],
                    "capital_high": row["capital_cost_cad_high"],
                    "vehicle_unit_basis": row["unit_cost_basis"],
                }
                for level, row in shuttle_rows.items()
            },
            "additivity_warning": "These class envelopes are not additive to results/vancouver_transition_scenarios.json. Removing shared depot/charger allocations from the non-deck baseline is required before combining them.",
            "price_basis_warning": "The scenarios mix nominal 2020/2021/2023/2024 evidence and explicit FX/uncertainty assumptions. They are budgets, not bids, invoices or present values.",
        },
        "unverifiable": [
            "Exact 31 December 2023 class/age/depot vehicle register",
            "Vehicle ID or garage assignment for each 2023 GTFS block",
            "Vancouver winter energy and state-of-charge for an Enviro500EV and each 20-passenger shuttle candidate",
            "Payload after batteries, accessibility equipment and winter heating; axle-weight approval for the deck",
            "Terminal layover duration and curb/site geometry for opportunity charging",
            "Firm site power, transformer capacity, utility interconnection cost and commissioning lead time",
            "Awarded, tax-inclusive North American deck contract specifically for TransLink and a delivered 16-20 passenger electric shuttle comparable to its current fleet",
            "Whether 57 deck duties and 171-206 shuttles can all be preserved without block splitting, additional vehicles or service constraints",
        ],
        "outputs": {
            "parameter_table": "data/processed/deck_shuttle_parameter_table.csv",
            "fleet_mapping": "data/processed/deck_shuttle_fleet_mapping.csv",
            "duty_screen": "data/processed/deck_shuttle_duty_screen_2023.csv",
            "scenarios": "data/processed/deck_shuttle_scenarios.csv",
            "research_note": "research/deck_shuttle_electrification_note.md",
        },
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "deck_shuttle_electrification_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "status": report["status"],
        "deck": deck_rows,
        "shuttle": shuttle_rows,
        "fleet_mapping": report["fleet_mapping"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
