"""Publish observed service scale and explicit unresolved gates for Vancouver."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from audit_service_actual import calculate as audit_actual_service
from model import check_schedule

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    audit = json.loads((ROOT / "data/processed/vancouver_data_audit.json").read_text())
    routes = pd.read_csv(ROOT / "data/processed/vancouver_route_annual_2023.csv")
    # Published average route speed times published revenue hours is a scale
    # estimator, not an odometer or a vehicle-block distance table.
    km_scale = float((routes.revenue_hours_2023 * routes.average_speed_kmh_2023).sum())
    actual_service = audit_actual_service()
    capacity_audit = json.loads((ROOT / "results/capacity_proxy_audit.json").read_text(
        encoding="utf-8"))
    site_check = check_schedule(None, None, None, None, None, year=2033)
    # 2019-CAD per 40-ft vehicle demonstration. The published depot BEB
    # still burns fuel for cabin heat and is NOT eligible for the strict
    # all-electric endpoint. It deliberately excludes
    # maintenance, driver, grid and battery replacement; it is no city result.
    diesel_bus_2019_cad = 630_000
    electric_bus_2019_cad = 1_110_000
    charger_2019_cad = 298_000
    diesel_l_per_km = 0.60
    electric_kwh_per_km = 1.4
    auxiliary_fuel_l_per_km = 0.02
    annual_km = 68_000
    litres = diesel_l_per_km * annual_km
    kwh = electric_kwh_per_km * annual_km
    demo = {
        "status": "ILLUSTRATIVE_ONLY",
        "price_basis": "2019 CAD; parameters published in the 2020 TransLink plan",
        "unit": "one 40-ft depot-charged bus versus one diesel bus, before replacement ratio",
        "2033_all_electric_eligible": False,
        "reason": "published depot BEB uses 0.02 L/km auxiliary fuel heat",
        "purchase_premium_cad": electric_bus_2019_cad - diesel_bus_2019_cad,
        "charger_per_bus_cad": charger_2019_cad,
        "annual_diesel_litres": litres,
        "annual_electricity_kwh": kwh,
        "annual_auxiliary_heater_litres": auxiliary_fuel_l_per_km * annual_km,
        "annual_grid_tco2e_at_2023_bc_integrated_factor": kwh * 0.0113 / 1000,
        "excluded": ["maintenance", "driver time", "grid upgrade", "battery replacement",
                     "vehicle quantity expansion", "residual value", "embodied emissions",
                     "incremental electricity for a fully electric cabin heater"],
    }
    output = {
        "case": "Metro Vancouver/TransLink fixed-route bus",
        "baseline_year": 2023,
        "observed": {
            "route_count": audit["annual_route_count"],
            "published_route_service_hours": audit["csv_annual_service_hours"],
            "statutory_bus_service_hours": audit["statutory_annual_service_hours"],
            "service_hour_coverage_ratio": audit["csv_to_statutory_service_hours_ratio"],
            "actual_2023_bus_service_hours_excluding_seabus": actual_service["bus_totals"]["service_hours"],
            "actual_2023_bus_service_km_excluding_seabus": actual_service["bus_totals"]["service_km"],
            "actual_2023_bus_capacity_km_excluding_seabus": actual_service["bus_totals"]["capacity_km"],
            "weighted_capacity_spaces_per_bus_service_km": actual_service["bus_totals"]["capacity_km"] / actual_service["bus_totals"]["service_km"],
            "positive_route_time_load_cells_matching_historical_capacity_clusters": capacity_audit["reference_capacity_matches"],
            "positive_route_time_load_cells_total": capacity_audit["input_2023_tspr_positive_cells"],
            "capacity_class_note": "Aggregate 2018 capacity references explain most 2023 route-time cells, but not individual 2023 bus assignments or candidate electric payload.",
            "revenue_fleet_2023_operating_ghg_all_modes_t": 112_591,
            "revenue_fleet_2023_scope1_t": 110_402,
            "revenue_fleet_2023_scope2_t": 2_189,
            "route_hour_coverage_of_exact_actual_bus_hours": actual_service["route_hours_share_of_exact_bus_hours"],
            "actual_service_source": actual_service["source"],
            "route_speed_times_revenue_hours_km_scale": round(km_scale),
            "distance_status": "OFFICIAL_SERVICE_KM_NOW_AVAILABLE; route speed×revenue hours remains a separate estimator",
            "dec_2023_trolley_plus_battery_electric_buses": 280,
            "feb_2023_trolley_buses": 262,
            "jun_2023_battery_electric_buses_technology_presentation": 4,
            "dec_2023_battery_electric_buses_official_blog_approx": 5,
            "dec_2023_trolley_buses_official_blog_approx": 275,
            "dec_2023_battery_electric_buses_conditional_if_feb_trolley_count_unchanged": 18,
            "cng_buses_2023": 299,
            "fleet_count_note": "December official release says 280 trolley+BEB; same-day official blog says about 275 trolley and five BEB; February notice says 262 trolley. These cannot establish an exact December class split. The 18-bus subtraction assumes unchanged trolley stock and conflicts with the same-day blog.",
            "fleet_count_sources": [
                "https://www.translink.ca/news/2023/december/metro%20vancouver%20diesel%20buses%20transitioning%20to%20cleaner%20renewable%20fuel",
                "https://www.translink.ca/news/2023/february/translink%20begins%20battery-electric%20bus%20fleet%20expansion",
                "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2023/june/agenda_mayors_council_public_mtg_june_2023.pdf",
                "https://buzzer.translink.ca/2023/12/translink-shifts-buses-from-fossil-fuels-to-100-per-cent-renewable-diesel/",
                "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/accountability_reports/2023/accountability_report_2023.pdf",
            ],
        },
        "retrospective_2024_facility_plan": {
            "port_coquitlam_beb_capacity_reported": ">100",
            "port_coquitlam_target_year": 2027,
            "marpole_beb_capacity_approx": 340,
            "marpole_target_year": 2028,
            "existing_depot_charging_delivery_years_range": [6, 8],
            "status": "PLANNED_IN_2024_NOT_COMMISSIONED_IN_2023",
            "source": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf",
        },
        "full_city_schedule_check": {
            "status": site_check.status,
            "missing": site_check.missing + ["2023 class/age/energy fleet register",
                                              "2023 exact timetable and block assignments",
                                              "depot space/grid/commissioning inventory",
                                              "per-trip 2023 class/capacity assignments",
                                              "candidate electric bus payload and winter accessory energy"],
        },
        "full_city_2033_feasibility": "UNVERIFIED",
        "full_city_cost_score": None,
        "full_city_environment_score": None,
        "full_city_pareto_frontier": None,
        "full_city_yearly_purchase_table": None,
        "separate_reference_case_file": "results/cpu_reference_scores.json",
        "transfer_case_result_files": {
            "chicago_2023_age_energy_and_renewal_bound": "results/cta_2023_detail_audit.json",
            "london_solved_cohort_roadmap": "results/london_cohort_roadmap.json",
        },
        "per_bus_calculation": demo,
    }
    dest = ROOT / "results/model_readiness.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
