"""Class-specific core-cost bound for Vancouver's fixed-route buses.

The existing conditional case keeps double-decks outside the battery-depot
arithmetic and prices community shuttles with a generic 40-ft unit. This audit
uses the separate 2023 GTFS class screen and public vehicle/site envelopes to
bring both classes into one transparent planning boundary. Shared heavy-bus
depot investment is retained once; each class receives only its separately
identified vehicle and charger envelope.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from build_transition_scenarios import allocate, pv, vehicle_residual_pv
from transition_ledger import service_ledger, operating_costs, use_emissions

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    vancouver = json.loads(
        (ROOT / "results/vancouver_transition_scenarios.json").read_text()
    )
    deck = pd.read_csv(ROOT / "data/processed/deck_shuttle_scenarios.csv")
    deck_rows = deck[deck.asset_class.eq("double_deck")].set_index("scenario")
    shuttle_rows = deck[deck.asset_class.eq("community_shuttle")].set_index("scenario")
    years = list(range(2024, 2034))
    # At 300 km, cap24 contributes 107 requests; the remaining heavy
    # (cap50 + unclassified + cap75) contributes 1,074 + 265 + 295 = 1,634
    # requests against 1,401 base blocks.
    # Retained integer scenario, NOT a rounded lower bound or dispatch result.
    heavy_positions = 1419
    existing_beb = 18
    heavy_purchases = heavy_positions - existing_beb
    heavy_standard_share = (1446 - 107) / ((1446 - 107) + 295)
    project_heavy_unit = (
        heavy_standard_share * (106_846_000 / 57)
        + (1 - heavy_standard_share) * 3_037_000
    )
    # Size the shared Marpole-style heavy-bus envelope from this scenario's
    # own heavy positions. Reusing the generic 1,612-position amount would
    # leave a shuttle allowance inside the shared depot and then add the
    # shuttle's dedicated site/charger envelope again.
    shared_depot_nominal = heavy_positions * (500_000_000.0 / 340.0)
    annual_standard_km = float(
        vancouver["service_baseline"]["annual_nondeck_fossil_km_estimate"]
    )
    deck_km = 5_450_000.0
    annual_full_km = annual_standard_km + deck_km
    annual_service = service_ledger(annual_full_km)
    om = {"conventional": 2.77, "beb": 2.28}
    rate = 0.03
    baseline_heavy_unit = 922_860.0
    # 54 conventional community shuttles, CAD 16.265m gross in the 2025 plan.
    baseline_shuttle_unit = 16_265_000.0 / 54
    # Existing trolleys must be renewed even though their propulsion is already
    # electric. These costs occur in both the renewal and electric scenarios.
    trolley_standard_schedule = allocate(188, list(range(2024, 2029)))
    trolley_pilot_schedule = {2026: 1}
    trolley_articulated_schedule = allocate(73, [2028, 2029])
    trolley_standard_unit = 414_600_000.0 / 188
    trolley_pilot_unit = 3_550_000.0
    trolley_articulated_unit = 182_900_000.0 / 73

    cases = []
    for name, heavy_unit in (("low", 1_200_000.0), ("central", 1_200_000.0),
                             ("high", project_heavy_unit)):
        d = deck_rows.loc[name]
        s = shuttle_rows.loc[name]
        shuttle_fleet = int(round(s.fleet_low))
        heavy_schedule = allocate(heavy_purchases, years)
        deck_schedule = allocate(57, years)
        shuttle_schedule = allocate(shuttle_fleet, years)
        heavy_fossil = 1725 - 262 - 57 - shuttle_fleet - existing_beb
        baseline_heavy = round(heavy_fossil * 10 / 17)
        baseline_shuttle = round(shuttle_fleet * 10 / 17)
        # The 57 double-decks were delivered during 2019--23, so none reaches
        # a 17-year chassis life before 2033. Their early conversion appears on
        # the electric side only; no resale credit is claimed for the replaced
        # stock, which keeps the plan cost conservative.
        baseline_purchase_count = baseline_heavy + baseline_shuttle
        baseline_heavy_schedule = allocate(baseline_heavy, years)
        baseline_shuttle_schedule = allocate(baseline_shuttle, years)

        heavy_vehicle = {y: heavy_schedule[y] * heavy_unit for y in years}
        deck_vehicle = {y: deck_schedule[y] * float(d.vehicle_unit_cost_cad_low) for y in years}
        shuttle_vehicle = {y: shuttle_schedule[y] * float(s.vehicle_unit_cost_cad_low) for y in years}
        extra_infrastructure = (
            float(d.infrastructure_cost_cad_low)
            + float(s.infrastructure_cost_cad_low)
        )
        infrastructure = shared_depot_nominal + extra_infrastructure
        infra_schedule = {y: infrastructure / 8.0 for y in range(2024, 2032)}
        shared_schedule = {y: shared_depot_nominal / 8.0 for y in range(2024, 2032)}
        class_infra_schedule = {y: extra_infrastructure / 8.0 for y in range(2024, 2032)}

        baseline_om, plan_om = operating_costs(annual_service, om["conventional"], om["beb"])
        trolley_capex = {
            y: trolley_standard_schedule.get(y, 0) * trolley_standard_unit
            + trolley_pilot_schedule.get(y, 0) * trolley_pilot_unit
            + trolley_articulated_schedule.get(y, 0) * trolley_articulated_unit
            for y in years
        }

        baseline_heavy_capex = {
            y: baseline_heavy_schedule[y] * baseline_heavy_unit for y in years
        }
        baseline_shuttle_capex = {
            y: baseline_shuttle_schedule[y] * baseline_shuttle_unit for y in years
        }
        base_residual_pv, base_residual = vehicle_residual_pv(
            {
                y: baseline_heavy_schedule[y] * baseline_heavy_unit
                + baseline_shuttle_schedule[y] * baseline_shuttle_unit
                for y in years
            },
            1.0,
        )
        heavy_residual_pv, heavy_residual = vehicle_residual_pv(
            heavy_schedule, heavy_unit
        )
        deck_residual_pv, deck_residual = vehicle_residual_pv(
            deck_schedule, float(d.vehicle_unit_cost_cad_low)
        )
        shuttle_residual_pv, shuttle_residual = vehicle_residual_pv(
            shuttle_schedule, float(s.vehicle_unit_cost_cad_low)
        )
        trolley_standard_residual_pv, trolley_standard_residual = vehicle_residual_pv(
            trolley_standard_schedule, trolley_standard_unit
        )
        trolley_articulated_residual_pv, trolley_articulated_residual = vehicle_residual_pv(
            trolley_articulated_schedule, trolley_articulated_unit
        )
        trolley_pilot_residual_pv, trolley_pilot_residual = vehicle_residual_pv(
            trolley_pilot_schedule, trolley_pilot_unit
        )
        base_cash = {
            y: baseline_heavy_capex[y] + baseline_shuttle_capex[y]
            + baseline_om[y] + trolley_capex[y]
            for y in years
        }
        base_cash[2033] += (
            base_residual.get(2033, 0.0)
            + trolley_standard_residual.get(2033, 0.0)
            + trolley_articulated_residual.get(2033, 0.0)
            + trolley_pilot_residual.get(2033, 0.0)
        )
        plan_cash = {
            y: heavy_vehicle[y] + deck_vehicle[y] + shuttle_vehicle[y]
            + trolley_capex[y] + infra_schedule.get(y, 0.0) + plan_om[y]
            for y in years
        }
        plan_cash[2033] += (
            heavy_residual.get(2033, 0.0)
            + deck_residual.get(2033, 0.0)
            + shuttle_residual.get(2033, 0.0)
            + trolley_standard_residual.get(2033, 0.0)
            + trolley_articulated_residual.get(2033, 0.0)
            + trolley_pilot_residual.get(2033, 0.0)
        )
        base_pv = pv(base_cash)
        plan_pv = pv(plan_cash)
        capital_pv = (
            pv(heavy_vehicle) + pv(deck_vehicle) + pv(shuttle_vehicle)
            + pv(infra_schedule)
        )
        cases.append({
            "case": name,
            "heavy_positions_after_service_scale": heavy_positions,
            "heavy_purchases_after_existing_beb": heavy_purchases,
            "shuttle_fleet": shuttle_fleet,
            "double_deck_fleet": 57,
            "baseline_purchase_count": baseline_purchase_count,
            "baseline_heavy_purchases": baseline_heavy,
            "baseline_shuttle_purchases": baseline_shuttle,
            "baseline_double_deck_purchases": 0,
            "baseline_heavy_unit_cost_cad": baseline_heavy_unit,
            "baseline_shuttle_unit_cost_cad": baseline_shuttle_unit,
            "heavy_unit_cost_cad": heavy_unit,
            "shared_depot_cad": shared_depot_nominal,
            "deck_core_capital_cad": float(d.capital_cost_cad_low),
            "shuttle_core_capital_cad": float(s.capital_cost_cad_low),
            "additional_class_capital_cad": extra_infrastructure,
            "capital_gross_nominal_cad": (
                sum(heavy_vehicle.values()) + sum(deck_vehicle.values())
                + sum(shuttle_vehicle.values()) + infrastructure
            ),
            "common_trolley_capital_nominal_cad": (
                trolley_standard_unit * 188
                + trolley_articulated_unit * 73 + trolley_pilot_unit
            ),
            "total_modeled_capital_nominal_cad": (
                sum(heavy_vehicle.values()) + sum(deck_vehicle.values())
                + sum(shuttle_vehicle.values()) + infrastructure
                + trolley_standard_unit * 188
                + trolley_articulated_unit * 73 + trolley_pilot_unit
            ),
            "baseline_gross_pv_cad": base_pv,
            "plan_gross_pv_cad": plan_pv,
            "economic_score_gross_pct": 100 * (base_pv - plan_pv) / base_pv,
            "incremental_gross_pv_cad": plan_pv - base_pv,
            "components_pv_cad": {
                "baseline_vehicle_capex": pv(baseline_heavy_capex)
                + pv(baseline_shuttle_capex),
                "baseline_om": pv(baseline_om),
                "baseline_residual": base_residual_pv,
                "plan_heavy_vehicle_capex": pv(heavy_vehicle),
                "plan_deck_vehicle_capex": pv(deck_vehicle),
                "plan_shuttle_vehicle_capex": pv(shuttle_vehicle),
                "common_trolley_replacement_capex": pv(trolley_capex),
                "plan_shared_heavy_depot": pv(shared_schedule),
                "plan_class_charger_infrastructure": pv(class_infra_schedule),
                "plan_om": pv(plan_om),
                "plan_residual": heavy_residual_pv + deck_residual_pv + shuttle_residual_pv,
                "common_trolley_replacement_residual": (
                    trolley_standard_residual_pv + trolley_articulated_residual_pv
                    + trolley_pilot_residual_pv
                ),
            },
            "grant_cases": [
                {
                    "grant_fraction": fraction,
                    "agency_pv_cad": plan_pv - fraction * capital_pv,
                    "agency_economic_score_vs_baseline_pct": 100 * (
                        base_pv - (plan_pv - fraction * capital_pv)
                    ) / base_pv,
                }
                for fraction in (0.0, 0.25, 0.50)
            ],
            "grant_eligible_capital_pv_cad": capital_pv,
            "grant_scope": "Incremental route-conversion capital only. Common trolley replacement is excluded because the same electric renewal is required in the ordinary-renewal comparator.",
            "grant_cases_with_common_trolley_capital": [
                {
                    "grant_fraction": fraction,
                    "agency_pv_cad": (
                        plan_pv - fraction * (capital_pv + pv(trolley_capex))
                    ),
                    "agency_economic_score_vs_baseline_pct": 100 * (
                        base_pv - (
                            plan_pv - fraction * (capital_pv + pv(trolley_capex))
                        )
                    ) / base_pv,
                }
                for fraction in (0.0, 0.25, 0.50)
            ],
        })

    # Central annual inventory certificate. The extra heavy positions are
    # added capacity required by range splitting, while conventional retirements
    # cover only the 1,445 non-electric buses in the 2023 bridge.
    heavy_retirements = 1217 - existing_beb
    deck_retirements = 57
    shuttle_retirements = 189
    heavy_schedule = allocate(heavy_purchases, years)
    deck_schedule = allocate(57, years)
    shuttle_schedule = allocate(189, years)
    heavy_retire_schedule = allocate(heavy_retirements, years)
    deck_retire_schedule = allocate(deck_retirements, years)
    shuttle_retire_schedule = allocate(shuttle_retirements, years)
    ev_stock = 262 + existing_beb
    conventional_stock = heavy_retirements + deck_retirements + shuttle_retirements
    annual_inventory = []
    for year in years:
        beb_bought = heavy_schedule[year] + deck_schedule[year] + shuttle_schedule[year]
        trolley_bought = (
            trolley_standard_schedule.get(year, 0)
            + trolley_articulated_schedule.get(year, 0)
            + trolley_pilot_schedule.get(year, 0)
        )
        ev_bought = beb_bought + trolley_bought
        conventional_retired = (
            heavy_retire_schedule[year] + deck_retire_schedule[year]
            + shuttle_retire_schedule[year]
        )
        ev_stock += ev_bought - trolley_bought
        conventional_stock -= conventional_retired
        annual_inventory.append({
            "year": year,
            "heavy_beb_purchases": heavy_schedule[year],
            "double_deck_beb_purchases": deck_schedule[year],
            "shuttle_beb_purchases": shuttle_schedule[year],
            "trolley_replacement_purchases": trolley_bought,
            "total_beb_purchases": beb_bought,
            "total_electric_vehicle_purchases": ev_bought,
            "conventional_retirements": conventional_retired,
            "electric_stock_end": ev_stock,
            "conventional_stock_end": conventional_stock,
        })
    assert conventional_stock == 0

    central = next(x for x in cases if x["case"] == "central")
    plan_production_t = (
        heavy_purchases * ((6.6 * 14_880 + 58 * 335) / 1000)
        + 189 * (58 * 150 / 1000)
        + 57 * ((6.6 * 14_880 + 58 * 700) / 1000)
    )
    # Symmetric partial boundary: omit unknown shuttle bodies on BOTH sides.
    baseline_heavy_count = round((1725 - 262 - 57 - 189 - existing_beb) * 10 / 17)
    baseline_production_t = baseline_heavy_count * (6.6 * 11_429 / 1000)
    environment = []
    for name, intensity in (("renewable_fuel_mix", .302), ("rng_heavy", .96),
                            ("weighted_mix", 1.233), ("fossil_diesel", 1.58)):
        use = use_emissions(annual_service, intensity)
        base_operating, plan_operating = use["baseline_operating_t"], use["plan_operating_t"]
        base_maintenance, plan_maintenance = use["baseline_maintenance_t"], use["plan_maintenance_t"]
        base_total = baseline_production_t + base_operating + base_maintenance
        plan_total = plan_production_t + plan_operating + plan_maintenance
        environment.append({
            "case": name,
            "baseline_operating_g_per_km": 1000 * intensity,
            **use,
            "baseline_production_t": baseline_production_t,
            "plan_production_t": plan_production_t,
            "avoided_emissions_t": base_total - plan_total,
            "baseline_boundary_t": base_total,
            "plan_boundary_t": plan_total,
            "environment_score_pct": 100 * (base_total - plan_total) / base_total,
        })

    output = {
        "status": "CONDITIONAL_CLASS_INVENTORY_COST_SCENARIO_NOT_DISPATCH_CERTIFIED",
        "pv_basis": "price-mixed screening PV: vehicle/site envelopes span 2021--2026 nominal CAD and are not rebased; the 3% rate is scenario arithmetic",
        "method": "1419 heavy positions is a retained proportional inventory scenario, not a vehicle requirement bound. The 18 existing BEBs and initial 1725 assets are unverified stock assumptions, not delivery records.",
        "annual_service_ledger": annual_service,
        "environment_denominator_scope": "Scored conversion-service subset; common trolley and retained BEB activity excluded. Not a whole-fleet percentage.",
        "manufacturing_boundary": {"baseline_heavy_proxy_count": baseline_heavy_count,
                                   "shuttle_body_both_paths": "OMITTED_UNKNOWN",
                                   "common_trolley_both_paths": "OMITTED_COMMON"},
        "classes": {
            "heavy_non_deck": heavy_positions,
            "double_deck": 57,
            "community_shuttle_midpoint": 189,
            "existing_beb": 18,
        },
        "service_km": {
            "current_non_deck_fossil_proxy": annual_standard_km,
            "double_deck_proxy": deck_km,
            "full_scored_proxy": annual_full_km,
            "community_shuttle_official_2023": 13_653_519,
        },
        "economics": cases,
        "environment_central": environment,
        "production_components_t_central": {
            "heavy_standard_proxy": heavy_purchases * ((6.6 * 14_880 + 58 * 335) / 1000),
            "community_shuttle_battery_only": 189 * (58 * 150 / 1000),
            "double_deck_standard_glider_proxy": 57 * ((6.6 * 14_880 + 58 * 700) / 1000),
            "omitted_or_proxy_components": [
                "community-shuttle body and powertrain production",
                "double-deck-specific body and powertrain mass",
                "articulated-bus-specific body and powertrain mass",
                "common new electric-trolley body and overhead-power hardware",
                "charging and depot construction",
                "end-of-life credits",
            ],
        },
        "central_result": central,
        "central_annual_inventory": annual_inventory,
        "initial_stock_2023": {
            "electric_trolleys": 262,
            "existing_beb": existing_beb,
            "conventional": heavy_retirements + deck_retirements + shuttle_retirements,
            "total": 262 + existing_beb + heavy_retirements + deck_retirements + shuttle_retirements,
        },
        "endpoint_2033": {
            "electric_stock": annual_inventory[-1]["electric_stock_end"],
            "conventional_stock": annual_inventory[-1]["conventional_stock_end"],
            "net_new_beb_purchases": sum(x["total_beb_purchases"] for x in annual_inventory),
            "trolley_replacement_purchases": sum(
                x["trolley_replacement_purchases"] for x in annual_inventory
            ),
            "total_electric_vehicle_purchases": sum(
                x["total_electric_vehicle_purchases"] for x in annual_inventory
            ),
            "additional_service_positions": annual_inventory[-1]["electric_stock_end"] - 1725,
        },
        "baseline_om_rate_sensitivity": [],
        "boundaries": [
            "Vehicle prices come from public planning or external procurement envelopes and mix 2021--2026 nominal currencies; they are not rebased to a single bid year.",
            f"Shared heavy-bus depot investment is sized from {heavy_positions} heavy positions and retained once. Class-specific charger/site items are added separately, but site power and civil works may still overlap.",
            "The double-deck annual distance is a weekday-share proxy; the shuttle distance is an independently published 2023 actual total.",
            "Shuttle and double-deck manufacturing inventories include battery factors; the shuttle glider mass is not invented.",
            "Depot construction and end-of-life are excluded from the environmental boundary.",
            "The financial envelope excludes post-2023 battery replacement, retained pre-2024 asset terminal values, disposal proceeds and infrastructure terminal value; opposing omissions mean this is not a conservative bound or complete TCO.",
        ],
    }
    central_plan_om_pv = pv({
        y: annual_full_km * (
            (1 - i / 10) * om["conventional"] + (i / 10) * om["beb"]
        ) for i, y in enumerate(years, start=1)
    })
    central_base_om_pv = pv({
        y: annual_full_km * om["conventional"] for y in years
    })
    for baseline_rate, label in ((1.97, "hybrid-rate low"),
                                 (2.77, "CNG-rate middle"),
                                 (3.30, "diesel-rate high")):
        base_om = pv({y: annual_full_km * baseline_rate for y in years})
        plan_om = pv({
            y: annual_full_km * (
                (1 - i / 10) * baseline_rate + (i / 10) * om["beb"]
            ) for i, y in enumerate(years, start=1)
        })
        base_total = central["baseline_gross_pv_cad"] - central_base_om_pv + base_om
        plan_total = central["plan_gross_pv_cad"] - central_plan_om_pv + plan_om
        output["baseline_om_rate_sensitivity"].append({
            "baseline_om_cad_per_vehicle_km": baseline_rate,
            "label": label,
            "economic_score_gross_pct": 100 * (base_total - plan_total) / base_total,
        })
    (ROOT / "results/vancouver_full_fleet_bound.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "classes": output["classes"],
        "economics": [{k: c[k] for k in (
            "case", "capital_gross_nominal_cad", "plan_gross_pv_cad",
            "economic_score_gross_pct", "grant_cases")}
            for c in cases],
        "environment_central": environment,
    }, indent=2))


if __name__ == "__main__":
    main()
