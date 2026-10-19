"""Conditional 2024--2033 fleet economics and emissions on 2023 service.

The active published block ratio is scaled onto a derived 1,711--1,733 2023
fleet bridge; unique block IDs are never called a garage roster. The selected
300-km case uses the historical electric-heat range planning point. Existing
trolleys remain overhead electric by route-capacity proxy. Double-deck blocks
are reported outside the scored battery-depot envelope because their in-route
charging and cost remain unverified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

try:
    from .transition_ledger import service_ledger, operating_costs, use_emissions
except ImportError:
    from transition_ledger import service_ledger, operating_costs, use_emissions

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"


def pv(cashflows: dict[int, float], base_year: int = 2023, rate: float = 0.03) -> float:
    return sum(value / (1 + rate) ** (year - base_year) for year, value in cashflows.items())


def allocate(count: int, years: range) -> dict[int, int]:
    years = list(years)
    quotient, remainder = divmod(count, len(years))
    return {year: quotient + (i < remainder) for i, year in enumerate(years)}


def vehicle_residual_pv(purchases: dict[int, int], unit_cost: float,
                        life_years: int = 17, horizon: int = 2033) -> tuple[float, dict[int, float]]:
    values = {}
    for year, count in purchases.items():
        age = horizon - year
        fraction = max(0.0, (life_years - age) / life_years)
        values[2033] = values.get(2033, 0.0) - count * unit_cost * fraction
    return pv(values), values


def main() -> None:
    range_audit = json.loads((ROOT / "results/vancouver_block_range_audit.json").read_text())
    weekday = next(d for d in range_audit["days"] if d["kind"] == "weekday")
    class_counts = {name: value["blocks"] for name, value in weekday["classes"].items()}
    non_trolley_blocks = sum(v for k, v in class_counts.items() if k not in {"cap47", "cap70"})
    target40 = next(x for x in weekday["range_scenarios"] if x["scenario"] == "40ft" and x["range_km"] == 300)["fleet_blocks_after_ceiling"]
    target60 = next(x for x in weekday["range_scenarios"] if x["scenario"] == "60ft" and x["range_km"] == 300)["fleet_blocks_after_ceiling"]
    double_deck = class_counts["cap85"]
    battery_depots = target40 + target60
    plan_battery = battery_depots
    battery_base40 = next(x for x in weekday["range_scenarios"] if x["scenario"] == "40ft" and x["range_km"] == 149)["battery_candidate_blocks"]
    battery_base60 = next(x for x in weekday["range_scenarios"] if x["scenario"] == "60ft" and x["range_km"] == 150)["battery_candidate_blocks"]
    main_non_trolley = battery_base40 + battery_base60
    fleet2023_total = 1725
    existing_trolleys = 262
    existing_beb = 18
    non_trolley_fleet = fleet2023_total - existing_trolleys
    nondeck_non_trolley_fleet = non_trolley_fleet - double_deck
    scaled_battery_plan = round(nondeck_non_trolley_fleet * plan_battery / main_non_trolley)
    net_new_batteries = scaled_battery_plan - existing_beb
    fossil_fleet_for_renewal = nondeck_non_trolley_fleet - existing_beb
    extra = scaled_battery_plan - nondeck_non_trolley_fleet
    # TransLink 2024 O&M per vehicle-km and 2024 fuel/energy intensity tables.
    om = {"diesel": 3.30, "hybrid": 1.97, "cng": 2.77, "beb": 2.28}
    operating_intensity = {"diesel": 1580, "hybrid": 1420, "cng": 1350, "rng": 250, "beb": 19}
    # For this fixed-service comparison, trolley-owned distances cancel. Build
    # fossil-share from the actual block distance interval to avoid allocating
    # the full 106.87 million bus-km to previously conventional vehicles.
    trolley_lower = weekday["classes"]["cap47"]["distance_lower_km"] + weekday["classes"]["cap70"]["distance_lower_km"]
    trolley_upper = weekday["classes"]["cap47"]["distance_upper_km"] + weekday["classes"]["cap70"]["distance_upper_km"]
    fossil_share_low = 1 - trolley_upper / weekday["distance_upper_km"]
    fossil_share_high = 1 - trolley_lower / weekday["distance_lower_km"]
    fossil_share = (fossil_share_low + fossil_share_high) / 2
    deck_share_upper = weekday["classes"]["cap85"]["distance_upper_km"] / weekday["distance_upper_km"]
    nondeck_service_share = max(0, fossil_share - deck_share_upper)
    annual_bus_km = 106_868_324.0
    annual_fossil_km = annual_bus_km * nondeck_service_share * (fossil_fleet_for_renewal / nondeck_non_trolley_fleet)

    # Source-labelled capital parameters. The high infrastructure value is the
    # 2024 screening envelope including service expansion and multi-site work;
    # it is a sensitivity, never an additive line item with Marpole alone.
    conventional_bus_cad = 46_143_000 / 50
    beb_hardware_cad = 1_200_000
    beb_project_envelope_cad = 1_874_000
    depot_per_bus_cad = 500_000_000 / 340
    onroute_charger_cad = 610_000
    high_infrastructure_cad = 6_520_000_000
    onroute_count = int(-(-double_deck // 8))
    years = range(2024, 2034)
    natural_renewal_fraction = 10 / 17
    baseline_purchases = allocate(round(fossil_fleet_for_renewal * natural_renewal_fraction), years)
    plan_purchases = allocate(net_new_batteries, years)
    annual_service = service_ledger(annual_fossil_km)
    econ_cases = []
    for name, infrastructure in [
        ("low", net_new_batteries * depot_per_bus_cad),
        ("central", net_new_batteries * depot_per_bus_cad),
        ("high", high_infrastructure_cad),
    ]:
        base_capex = {y: baseline_purchases[y] * conventional_bus_cad for y in years}
        if name == "high":
            target40_scaled = round(net_new_batteries * target40 / plan_battery)
            target60_scaled = net_new_batteries - target40_scaled
            plan_unit_price = ((target40_scaled * beb_project_envelope_cad
                                + target60_scaled * 3_037_000) / net_new_batteries)
        else:
            plan_unit_price = beb_hardware_cad
        plan_capex = {y: plan_purchases[y] * plan_unit_price for y in years}
        infra_years = list(range(2024, 2032))
        infra_capex = {y: infrastructure / len(infra_years) for y in infra_years}
        baseline_om, plan_om = operating_costs(annual_service, om["cng"], om["beb"])
        baseline_residual_pv, baseline_residual = vehicle_residual_pv(baseline_purchases, conventional_bus_cad)
        plan_residual_pv, plan_residual = vehicle_residual_pv(plan_purchases, plan_unit_price)
        base_cash = {y: base_capex[y] + baseline_om[y] for y in years}
        plan_cash = {y: plan_capex[y] + infra_capex.get(y, 0.0) + plan_om[y] for y in years}
        base_cash[2033] += baseline_residual.get(2033, 0.0)
        plan_cash[2033] += plan_residual.get(2033, 0.0)
        base_pv, plan_pv = pv(base_cash), pv(plan_cash)
        eligible_capital_pv = pv(plan_capex) + pv(infra_capex)
        grants = []
        for fraction in (0, .25, .5):
            agency = plan_pv - fraction * eligible_capital_pv
            grants.append({"grant_fraction": fraction, "agency_pv_cad": agency,
                           "grant_transfer_pv_cad": fraction * eligible_capital_pv,
                           "agency_economic_score_vs_baseline_pct": 100 * (base_pv - agency) / base_pv})
        econ_cases.append({"case": name, "beb_unit_cost_cad": plan_unit_price,
            "beb_cost_basis": "all-class hardware lower bound" if name != "high" else "identified standard/articulated project-envelope weighted mean",
            "infrastructure_gross_cad": infrastructure,
            "baseline_gross_pv_cad": base_pv, "baseline_bus_capex_cad": sum(base_capex.values()),
            "plan_gross_pv_cad": plan_pv, "plan_bus_capex_cad": sum(plan_capex.values()),
            "components_pv_cad": {"baseline_bus_capex": pv(base_capex),
                                  "baseline_om": pv(baseline_om),
                                  "baseline_vehicle_residual": baseline_residual_pv,
                                  "plan_bus_capex": pv(plan_capex), "plan_infrastructure": pv(infra_capex),
                                  "plan_om": pv(plan_om), "plan_vehicle_residual": plan_residual_pv},
            "incremental_gross_pv_cad": plan_pv - base_pv,
            "economic_score_gross_pct": 100 * (base_pv - plan_pv) / base_pv,
            "vehicle_residual_credit_pv_cad": -(plan_residual_pv - baseline_residual_pv),
            "grant_cases": grants})
    # Conditional environmental inventory over the same ten years. Production
    # factors are a transfer sensitivity from ICCT, not Vancouver measurements.
    beb_production_t = (6.6 * 14_880 + 58 * 335) / 1000
    diesel_production_t = 6.6 * 11_429 / 1000
    base_prod = round(fossil_fleet_for_renewal * natural_renewal_fraction) * diesel_production_t
    plan_prod = net_new_batteries * beb_production_t
    env_cases = []
    for name, intensity_kg_km in [("renewable_fuel_mix", .302), ("rng_heavy", .96),
                                   ("weighted_mix", 1.233), ("fossil_diesel", 1.58)]:
        use = use_emissions(annual_service, intensity_kg_km)
        base_operating, plan_operating = use["baseline_operating_t"], use["plan_operating_t"]
        base_maintenance, plan_maintenance = use["baseline_maintenance_t"], use["plan_maintenance_t"]
        base_total = base_prod + base_operating + base_maintenance
        plan_total = plan_prod + plan_operating + plan_maintenance
        env_cases.append({"case": name, "baseline_operating_g_per_km": 1000 * intensity_kg_km,
                          "baseline_lifecycle_boundary_t": base_total, "plan_lifecycle_boundary_t": plan_total,
                          "environment_score_boundary_pct": 100 * (base_total - plan_total) / base_total,
                          "baseline_production_t": base_prod, "plan_production_t": plan_prod,
                          "baseline_operating_t": base_operating, "plan_operating_t": plan_operating,
                          "baseline_maintenance_t": base_maintenance, "plan_maintenance_t": plan_maintenance})
    output = {"status": "CONDITIONAL_EXECUTED_SCENARIO_NOT_CERTIFIED_CITY_OPTIMUM",
              "service_baseline": {"source_day": weekday["date"],
                                   "derived_2023_fleet_total": fleet2023_total,
                                   "derived_2023_non_trolley_fleet": non_trolley_fleet,
                                   "active_non_trolley_blocks": main_non_trolley,
                                   "capacity_proxy_blocks_not_purchased": class_counts["cap47"] + class_counts["cap70"],
                                   "selected_range_km": 300, "battery_depot_block_requests": battery_depots,
                                   "double_deck_in_route_blocks": double_deck,
                                   "scaled_battery_fleet_positions": scaled_battery_plan,
                                   "net_new_battery_purchases": net_new_batteries,
                                   "additional_active_block_requests": extra,
                                   "additional_active_block_requests_pct": 100 * extra / nondeck_non_trolley_fleet,
                                   "annual_2023_bus_km": annual_bus_km, "fossil_service_share": fossil_share,
                                   "annual_nondeck_fossil_km_estimate": annual_fossil_km},
              "annual_service_ledger": annual_service,
              "battery_replacement_stress": {
                  "status": "ILLUSTRATIVE_NOT_A_PREDICTED_REPLACEMENT",
                  "batteries": plan_purchases[2024], "capacity_kwh": 335,
                  "added_production_t": plan_purchases[2024] * 335 * 58 / 1000,
                  "renewable_mix_score_pct": 100 * (env_cases[0]["baseline_lifecycle_boundary_t"]
                      - env_cases[0]["plan_lifecycle_boundary_t"] - plan_purchases[2024] * 335 * 58 / 1000)
                      / env_cases[0]["baseline_lifecycle_boundary_t"]},
              "economics": econ_cases, "environment": env_cases,
              "roadmap": [{"year": y, "baseline_bus_purchases": baseline_purchases[y],
                           "plan_bus_purchases": plan_purchases[y], "plan_electric_share_pct": 10 * (y - 2023),
                           "infrastructure_phase": y <= 2031} for y in years],
              "assumptions": {"fleet_2023_total": fleet2023_total, "fleet_2023_interval": [1711, 1733],
                              "existing_trolleys": existing_trolleys,
                              "existing_beb_scenario_asset_count": existing_beb,
                              "existing_beb_in_service_approx": 5,
                              "existing_beb_note": "18 is an unverified cross-date subtraction scenario, not a delivery record. About five were reported in service; 1725 and 1711--1733 are scenario choices, not verified stock or bounds.",
                              "double_deck_blocks_excluded": double_deck,
                              "baseline_natural_renewal_fraction": natural_renewal_fraction,
                              "conventional_bus_envelope_cad": conventional_bus_cad,
                              "baseline_cng_project_source": "2024 Business Plan, 50-bus project CAD 46.143m",
                              "beb_hardware_source": "June-2023 screening price CAD 1.2m",
                              "beb_project_envelope_source": "2025 Business Plan, CAD 1.874m per planned bus; retrospective",
                              "depot_per_bus_source": "June-2023 Marpole CAD 500m / 340 BEBs",
                              "onroute_charger_source": "June-2023 CAD 0.46--0.61m each",
                              "high_infrastructure_source": "2024 screening: CAD 6.52bn; includes expansion/multi-site scope",
                              "om_source": "2024 ZEFTP per vehicle-km; applied only to fossil-share service for both cases",
                              "production_source": "ICCT 2024 transfer factors; 6.6 kg/kg; 58 kgCO2e/kWh LFP; 335kWh/14,880kg BEB; 11,429kg diesel",
                              "discount_rate": .03, "vehicle_life_years": 17,
                              "pv_basis": "price-mixed screening PV: public envelopes span 2021--2025 nominal CAD and are not rebased; the 3% rate is applied for scenario arithmetic, not presented as a constant-dollar bid appraisal",
                              "capital_schedule": "baseline 10/17 steady-state renewals and electric plan spread 2024-2033; infrastructure 2024-2031",
                              "residual": "vehicle straight-line by 17-year life; infrastructure residual excluded"},
              "limits": ["Task-ratio scaling is an inventory assumption, neither a lower nor upper bound on required vehicles; it does not certify service or standby buses.",
                         "The 300-km point is a historical planning sensitivity, not a certified 2033 procurement specification.",
                         "Double-deck blocks are outside the scored battery-depot envelope; their in-route charging and cost remain unverified.",
                         "The high infrastructure envelope includes service expansion and must not be presented as fixed-service cost.",
                         "Environmental numbers exclude charging/depot construction and end-of-life credits; that boundary is named explicitly.",
                         "Capacity-specific trolley-route blocks are retained as proxies for already electric service; the feed does not certify propulsion.",
                         "The 2023 fleet total 1725 and grid 1711--1733 are scenario parameters; the dated snapshots do not prove bounds on 2023 stock.",
                         "The 10/17 natural-renewal fraction assumes a uniform age distribution; the missing 2023 age roster remains a real uncertainty."]}
    (ROOT / "results/vancouver_transition_scenarios.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"service_baseline": output["service_baseline"], "economics": econ_cases, "environment": env_cases}, indent=2))


if __name__ == "__main__":
    main()
