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

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    vancouver = json.loads(
        (ROOT / "results/vancouver_transition_scenarios.json").read_text()
    )
    deck = pd.read_csv(ROOT / "data/processed/deck_shuttle_scenarios.csv")
    deck_rows = deck[deck.asset_class.eq("double_deck")].set_index("scenario")
    shuttle_rows = deck[deck.asset_class.eq("community_shuttle")].set_index("scenario")
    current = next(x for x in vancouver["economics"] if x["case"] == "central")

    years = list(range(2024, 2034))
    heavy_positions = int((1406 - 189) * (1741 - 101) / (1502 - 101))
    existing_beb = 18
    heavy_purchases = heavy_positions - existing_beb
    heavy_standard_share = (1446 - 101) / ((1446 - 101) + 295)
    project_heavy_unit = (
        heavy_standard_share * (106_846_000 / 57)
        + (1 - heavy_standard_share) * 3_037_000
    )
    shared_depot_nominal = float(current["infrastructure_gross_cad"])
    annual_standard_km = float(
        vancouver["service_baseline"]["annual_nondeck_fossil_km_estimate"]
    )
    deck_km = 5_450_000.0
    annual_full_km = annual_standard_km + deck_km
    om = {"conventional": 2.77, "beb": 2.28}
    rate = 0.03
    baseline_purchase_count = 816
    baseline_unit = 922_860.0

    cases = []
    for name, heavy_unit in (("low", 1_200_000.0), ("central", 1_200_000.0),
                             ("high", project_heavy_unit)):
        d = deck_rows.loc[name]
        s = shuttle_rows.loc[name]
        shuttle_fleet = int(round(s.fleet_low))
        heavy_schedule = allocate(heavy_purchases, years)
        deck_schedule = allocate(57, years)
        shuttle_schedule = allocate(shuttle_fleet, years)
        baseline_schedule = allocate(baseline_purchase_count, years)

        heavy_vehicle = {y: heavy_schedule[y] * heavy_unit for y in years}
        deck_vehicle = {y: deck_schedule[y] * float(d.vehicle_unit_cost_cad_low) for y in years}
        shuttle_vehicle = {y: shuttle_schedule[y] * float(s.vehicle_unit_cost_cad_low) for y in years}
        extra_infrastructure = (
            float(d.infrastructure_cost_cad_low)
            + float(s.infrastructure_cost_cad_low)
        )
        infrastructure = shared_depot_nominal + extra_infrastructure
        infra_schedule = {y: infrastructure / 8.0 for y in range(2024, 2032)}

        baseline_om = {
            y: annual_full_km * om["conventional"] for y in years
        }
        plan_om = {}
        for i, y in enumerate(years, start=1):
            electric_share = i / 10
            plan_om[y] = annual_full_km * (
                (1 - electric_share) * om["conventional"]
                + electric_share * om["beb"]
            )

        base_residual_pv, base_residual = vehicle_residual_pv(
            baseline_schedule, baseline_unit
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
        base_cash = {
            y: baseline_schedule[y] * baseline_unit + baseline_om[y]
            for y in years
        }
        base_cash[2033] += base_residual.get(2033, 0.0)
        plan_cash = {
            y: heavy_vehicle[y] + deck_vehicle[y] + shuttle_vehicle[y]
            + infra_schedule.get(y, 0.0) + plan_om[y]
            for y in years
        }
        plan_cash[2033] += (
            heavy_residual.get(2033, 0.0)
            + deck_residual.get(2033, 0.0)
            + shuttle_residual.get(2033, 0.0)
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
            "heavy_unit_cost_cad": heavy_unit,
            "shared_depot_cad": shared_depot_nominal,
            "deck_core_capital_cad": float(d.capital_cost_cad_low),
            "shuttle_core_capital_cad": float(s.capital_cost_cad_low),
            "additional_class_capital_cad": extra_infrastructure,
            "capital_gross_nominal_cad": (
                sum(heavy_vehicle.values()) + sum(deck_vehicle.values())
                + sum(shuttle_vehicle.values()) + infrastructure
            ),
            "baseline_gross_pv_cad": base_pv,
            "plan_gross_pv_cad": plan_pv,
            "economic_score_gross_pct": 100 * (base_pv - plan_pv) / base_pv,
            "incremental_gross_pv_cad": plan_pv - base_pv,
            "components_pv_cad": {
                "baseline_vehicle_capex": pv({y: baseline_schedule[y] * baseline_unit for y in years}),
                "baseline_om": pv(baseline_om),
                "baseline_residual": base_residual_pv,
                "plan_heavy_vehicle_capex": pv(heavy_vehicle),
                "plan_deck_vehicle_capex": pv(deck_vehicle),
                "plan_shuttle_vehicle_capex": pv(shuttle_vehicle),
                "plan_shared_and_class_infrastructure": pv(infra_schedule),
                "plan_om": pv(plan_om),
                "plan_residual": heavy_residual_pv + deck_residual_pv + shuttle_residual_pv,
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
        })

    central = next(x for x in cases if x["case"] == "central")
    plan_production_t = (
        heavy_purchases * ((6.6 * 14_880 + 58 * 335) / 1000)
        + 189 * (58 * 150 / 1000)
        + 57 * ((6.6 * 14_880 + 58 * 700) / 1000)
    )
    baseline_production_t = baseline_purchase_count * (6.6 * 11_429 / 1000)
    environment = []
    for name, intensity in (("renewable_fuel_mix", .302), ("rng_heavy", .96),
                            ("weighted_mix", 1.233), ("fossil_diesel", 1.58)):
        base_operating = annual_full_km * 10 * intensity / 1000
        plan_operating = annual_full_km * 10 * .019 / 1000
        base_maintenance = annual_full_km * 10 * .0524 / 1000
        plan_maintenance = annual_full_km * 10 * .0675 / 1000
        base_total = baseline_production_t + base_operating + base_maintenance
        plan_total = plan_production_t + plan_operating + plan_maintenance
        environment.append({
            "case": name,
            "baseline_operating_g_per_km": 1000 * intensity,
            "baseline_boundary_t": base_total,
            "plan_boundary_t": plan_total,
            "environment_score_pct": 100 * (base_total - plan_total) / base_total,
        })

    output = {
        "status": "EXECUTED_CLASS_SPECIFIC_CORE_BOUND_NOT_AWARDED_BID",
        "method": "The 1,630 generic non-deck positions are reduced by the 207-position community-shuttle allowance, then scaled to 1,424 heavy positions; 18 existing BEB positions are retained.",
        "classes": {
            "heavy_non_deck": 1424,
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
        "central_result": central,
        "boundaries": [
            "Vehicle prices come from public planning or external procurement envelopes and mix 2021, 2023 and 2024 nominal currencies; they are not rebased to a single bid year.",
            "Shared heavy-bus depot investment is retained once. Class-specific charger/site items are added separately, but site power and civil works may still overlap.",
            "The double-deck annual distance is a weekday-share proxy; the shuttle distance is an independently published 2023 actual total.",
            "Shuttle and double-deck manufacturing inventories include battery factors; the shuttle glider mass is not invented.",
            "Depot construction and end-of-life are excluded from the environmental boundary.",
        ],
    }
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
