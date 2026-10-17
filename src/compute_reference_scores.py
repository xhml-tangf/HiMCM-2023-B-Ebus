"""CPU calculation of sourced, narrow bus-electrification benchmarks.

These are NOT the 2024-2033 whole-fleet optimization scores. The source's
published life-cycle cost is a historical 40-ft-bus model, and the emissions
calculation is operational only. All inputs and boundaries are in the JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from model import score


ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "fleet_plan": "https://www.translink.ca/-/media/translink/documents/about-translink/policies/translink_low_carbon_fleet_transition_plan_2020_02_24.pdf",
    "bc_grid": "https://www2.gov.bc.ca/gov/content/environment/climate-change/data/electricity",
    "federal_ghg_module": "https://housing-infrastructure.canada.ca/zero-emissions-trans-zero-emissions/ghg-modules-ges-eng.html",
    "accountability": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/accountability_reports/2023/accountability_report_2023.pdf",
    "fleet_update_2020": "https://www.translink.ca/-/media/translink/media-releases/2021/january/translink_low_carbon_fleet_transition_plan_update_2021_01_18.pdf",
    "zeftp_2024": "https://www.translink.ca/-/media/translink/documents/about-translink/governance-and-board/council-minutes-and-reports/2024/november/agenda--mayors-council--public-mtg--nov-28-2024.pdf",
}


def calculate() -> dict:
    # TransLink 2020 fleet plan, Appendix D, Table D-1 and p. D-2.
    # 2019 CAD per vehicle-km over its modeled complete service life.
    diesel_cost_per_km = 4.62
    hybrid_cost_per_km = 4.77
    cng_cost_per_km = 4.15
    in_route_beb_cost_per_km = 4.86
    depot_beb_cost_per_km = 5.14
    annual_km = 68_000
    diesel_l_per_km = 0.60
    # In-route BEB in Table D-1 uses 1.6 kWh/km and NO auxiliary fuel.
    # The depot BEB in the same table uses diesel cabin heat and is excluded.
    electric_kwh_per_km = 1.60
    diesel_price_2019_cad_l = 1.04
    electricity_price_2019_cad_kwh = 0.10

    # Federal Zero Emission Transit Fund GHG+ module, Annex D: heavy-duty
    # Diesel (B4), 2.630 kg CO2e/L. This is COMBUSTION, not fuel supply.
    diesel_tailpipe_kg_l = 2.630
    # BC Integrated Grid 2023 EEIF: 11.3 tCO2e/GWh = 0.0113 kg/kWh.
    bc_grid_kg_kwh = 0.0113

    diesel_kg_km = diesel_l_per_km * diesel_tailpipe_kg_l
    electric_kg_km = electric_kwh_per_km * bc_grid_kg_kwh

    baseline_cost = diesel_cost_per_km
    electric_cost = in_route_beb_cost_per_km
    ten_year_km = 10 * annual_km

    # Price thresholds hold all other lifetime cost-model terms constant.
    diesel_break_even_cad_l = diesel_price_2019_cad_l + (
        electric_cost - baseline_cost
    ) / diesel_l_per_km
    electricity_break_even_at_reference_diesel_cad_kwh = (
        electricity_price_2019_cad_kwh
        + (baseline_cost - electric_cost) / electric_kwh_per_km
    )
    grid_break_even_kg_kwh = diesel_kg_km / electric_kwh_per_km
    grid_for_95pct_reduction_kg_kwh = 0.05 * grid_break_even_kg_kwh
    historical_grid_kg_kwh = {2020: 0.0401, 2023: 0.0113, 2024: 0.0099}
    energy_cases_kwh_km = (1.37, 1.60, 2.00)
    operational_sensitivity = [
        {
            "grid_factor_year": year,
            "grid_kg_co2e_per_kwh": grid,
            "bus_energy_kwh_per_km": energy,
            "operational_ghg_score_pct": score(diesel_kg_km, grid * energy),
        }
        for year, grid in historical_grid_kg_kwh.items()
        for energy in energy_cases_kwh_km
    ]

    # A renewal comparator cannot be selected from the diesel reference alone.
    # TransLink's Appendix D supplies three historical conventional alternatives.
    historical_renewal_comparators = {
        name: {
            "historical_lifetime_cost_2019_cad_per_km": cost,
            "economic_score_vs_in_route_beb_pct": score(cost, electric_cost),
            "incremental_beb_cost_2019_cad_per_km": electric_cost - cost,
        }
        for name, cost in {
            "diesel": diesel_cost_per_km,
            "hybrid": hybrid_cost_per_km,
            "cng": cng_cost_per_km,
        }.items()
    }
    # ZEFTP 2024 Attachment 3, p. 18-19: operating and maintenance only.
    # Different price year/boundary from the 2020 lifetime table above.
    om_2024_cad_per_vehicle_km = {
        "diesel": 3.30,
        "hybrid": 1.97,
        "cng": 2.77,
        "beb": 2.28,
        "trolley": 4.12,
    }
    om_2024_comparison = {
        name: {
            "conventional_om_2024_cad_per_vehicle_km": cost,
            "beb_om_2024_cad_per_vehicle_km": om_2024_cad_per_vehicle_km["beb"],
            "om_only_score_pct": score(cost, om_2024_cad_per_vehicle_km["beb"]),
        }
        for name, cost in om_2024_cad_per_vehicle_km.items()
        if name in ("diesel", "hybrid", "cng")
    }
    # ZEFTP 2024 Attachment 3 operational emissions per vehicle-km;
    # renewable fuels remain non-electric despite their lower GHG intensity.
    ghg_2024_g_per_vehicle_km = {
        "fossil_diesel": 1580,
        "renewable_diesel": 530,
        "fossil_hybrid": 1420,
        "renewable_hybrid": 480,
        "fossil_cng": 1350,
        "renewable_cng": 250,
        "beb_electric_heater": 19,
    }
    ghg_2024_comparison = {
        name: score(value, ghg_2024_g_per_vehicle_km["beb_electric_heater"])
        for name, value in ghg_2024_g_per_vehicle_km.items()
        if name != "beb_electric_heater"
    }

    result = {
        "status": "CALCULATED_REFERENCE_CASE_ONLY",
        "cpu_method": "deterministic arithmetic and analytic break-even calculation; no solver or GPU needed for these identified inputs",
        "scope": "one equivalent 40-ft standard-bus service cohort; same vehicle-km, historical TransLink lifetime cost model",
        "not_whole_city_or_2024_2033_score": True,
        "sources": SOURCES,
        "historical_renewal_comparators": historical_renewal_comparators,
        "retrospective_2024_om_only_comparators": om_2024_comparison,
        "retrospective_2024_operational_ghg_intensity_g_per_vehicle_km": ghg_2024_g_per_vehicle_km,
        "retrospective_2024_operational_ghg_scores_pct": ghg_2024_comparison,
        "inputs": {
            "diesel_lifecycle_cost_2019_cad_per_km": diesel_cost_per_km,
            "hybrid_lifecycle_cost_2019_cad_per_km": hybrid_cost_per_km,
            "cng_lifecycle_cost_2019_cad_per_km": cng_cost_per_km,
            "in_route_all_electric_lifecycle_cost_2019_cad_per_km": electric_cost,
            "depot_beb_lifecycle_cost_2019_cad_per_km_ineligible_diesel_heat": depot_beb_cost_per_km,
            "annual_km_assumed_by_source": annual_km,
            "diesel_l_per_km": diesel_l_per_km,
            "in_route_electric_kwh_per_km": electric_kwh_per_km,
            "diesel_price_2019_cad_per_l": diesel_price_2019_cad_l,
            "electricity_price_2019_cad_per_kwh": electricity_price_2019_cad_kwh,
            "heavy_duty_diesel_combustion_kg_co2e_per_l": diesel_tailpipe_kg_l,
            "bc_2023_integrated_grid_kg_co2e_per_kwh": bc_grid_kg_kwh,
        },
        "reference_scores": {
            "economic_lifecycle_cost_score_pct": score(baseline_cost, electric_cost),
            "environment_operational_ghg_score_pct": score(diesel_kg_km, electric_kg_km),
            "environment_lifecycle_ghg_score_pct": None,
            "diesel_lifetime_model_cost_2019_cad_per_km": baseline_cost,
            "electric_lifetime_model_cost_2019_cad_per_km": electric_cost,
            "incremental_lifetime_model_cost_2019_cad_per_km": electric_cost - baseline_cost,
            "diesel_operational_kg_co2e_per_km": diesel_kg_km,
            "electric_operational_kg_co2e_per_km": electric_kg_km,
            "annual_diesel_operational_t_co2e": annual_km * diesel_kg_km / 1000,
            "annual_electric_operational_t_co2e": annual_km * electric_kg_km / 1000,
            "annual_operational_ghg_saving_t_co2e": annual_km * (diesel_kg_km - electric_kg_km) / 1000,
            "historical_cost_per_operational_t_co2e_avoided_2019_cad": (
                (electric_cost - baseline_cost) * 1000 / (diesel_kg_km - electric_kg_km)
            ),
        },
        "thresholds_holding_other_costs_fixed": {
            "diesel_price_for_cost_parity_2019_cad_per_l_at_0_10_cad_per_kwh": diesel_break_even_cad_l,
            "electricity_price_for_cost_parity_2019_cad_per_kwh_at_1_04_cad_per_l": electricity_break_even_at_reference_diesel_cad_kwh,
            "grid_intensity_for_operational_ghg_parity_kg_co2e_per_kwh": grid_break_even_kg_kwh,
            "max_grid_intensity_for_95pct_operational_ghg_reduction_kg_co2e_per_kwh": grid_for_95pct_reduction_kg_kwh,
            "ten_year_operational_ghg_saving_t_per_equivalent_bus_at_68000_km_per_year": ten_year_km * (diesel_kg_km - electric_kg_km) / 1000,
        },
        "historical_grid_and_source_energy_sensitivity": operational_sensitivity,
        "2023_reported_emissions_by_mode_g_co2e_per_passenger_km": {
            "diesel_bus": 100,
            "natural_gas_bus": 23,
            "battery_electric_bus": 2,
            "diesel_to_battery_electric_intensity_reduction_pct": score(100, 2),
            "natural_gas_to_battery_electric_intensity_reduction_pct": score(23, 2),
            "source_note": "TransLink 2023 Accountability Report; observed fleet mix, occupancy and renewable gas accounting differ from the 40-ft model",
        },
        "limitations": [
            "TransLink's lifetime cost values are historical 2019-CAD model outputs, not discounted 2024-2033 project costs.",
            "The in-route all-electric configuration has no auxiliary fuel in the source table; its required 450-kW charger availability and actual timetable feasibility are unverified for 2023 routes.",
            "Operational GHG omits diesel upstream fuel production, vehicle and battery manufacture, infrastructure, maintenance, and end of life.",
            "The 2023 BC grid factor is an annual accounting average; marginal generation and future grid intensity can differ.",
            "Existing trolleybuses and natural-gas buses mean these diesel-versus-BEB results cannot be multiplied across the full fleet.",
            "The 2023 class-by-service normal-renewal mix is unknown; the diesel reference economic score is not the fleet economic score. Hybrid and CNG comparator scores are reported separately.",
            "2024 ZEFTP operating/maintenance costs and GHG intensities are retrospective checks, with different boundaries and price year from the 2020 lifetime-cost model.",
        ],
    }
    return result


if __name__ == "__main__":
    output = calculate()
    destination = ROOT / "results" / "cpu_reference_scores.json"
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))
