"""Add source-labelled infrastructure embodied emissions to the horizon LCA.

The floor-area case uses Marpole's 800,000-square-foot aggregate building
area and 340-bus capacity, scaled linearly to the modeled heavy positions.
No bus bought in 2029--33 reaches end of life by 2033. Vehicle decommissioning
is therefore outside the horizon; charger equipment lifecycle (production,
transport, installation, decommissioning) is included.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQFT_TO_M2 = 0.09290304


def main() -> None:
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    heavy_positions = int(full["classes"]["heavy_non_deck"])
    shuttle_count = int(full["classes"]["community_shuttle_midpoint"])
    deck_count = int(full["classes"]["double_deck"])
    # Source ranges bracket charging equipment production/transport/
    # installation/decommissioning from Zhao 2022: 4.269--8.539 t each.
    charger_counts = {
        "heavy_depot": heavy_positions,
        "double_deck": 9,
        "community_shuttle": math.ceil(shuttle_count/2),
    }
    charger_low_t = sum(charger_counts.values()) * 4.2693
    charger_high_t = sum(charger_counts.values()) * 8.5386
    marpole_floor_m2 = 800_000 * SQFT_TO_M2
    modeled_floor_m2 = marpole_floor_m2 * heavy_positions / 340
    depot_embodied_t = modeled_floor_m2 * 650 / 1000
    infra_low_t = depot_embodied_t + charger_low_t
    infra_high_t = depot_embodied_t + charger_high_t
    cases = []
    for item in full["environment_central"]:
        for bound, infra in (("low", infra_low_t), ("high", infra_high_t)):
            plan = item["plan_boundary_t"] + infra
            cases.append({"fuel_case": item["case"], "equipment_bound": bound,
                          "baseline_t": item["baseline_boundary_t"], "plan_t": plan,
                          "infrastructure_t": infra,
                          "environment_score_pct": 100*(item["baseline_boundary_t"]-plan)/item["baseline_boundary_t"]})
    output = {
        "status": "HORIZON_LCA_WITH_SOURCE_LABELLED_INFRASTRUCTURE_SCENARIO",
        "horizon": [2024, 2033],
        "charger_count": charger_counts,
        "charger_equipment_t_per_unit_range": [4.2693, 8.5386],
        "depot_area": {"source_sqft": 800000, "source_capacity_buses": 340,
                       "source_m2": marpole_floor_m2, "modeled_m2": modeled_floor_m2,
                       "embodied_factor_kgco2e_per_m2": 650,
                       "depot_embodied_t": depot_embodied_t},
        "infrastructure_t_range": [infra_low_t, infra_high_t],
        "cases": cases,
        "included": ["vehicle/battery production proxies", "shared service ledger",
                     "maintenance and energy", "charging equipment lifecycle",
                     "depot building structure and envelope at a 650 kgCO2e/m2 scenario"],
        "excluded_because_outside_horizon": [
            "end-of-life of buses purchased in 2029--2033 (first cohort reaches age 8 in 2037)",
            "post-2033 service, battery replacements and infrastructure decommissioning"],
        "remaining_proxy": ["shuttle body/powertrain", "deck-specific body mass",
                            "articulated body mass", "common trolley body"],
        "source_boundary": "The floor-area factor and charger equipment case come from non-TransLink LCA studies and are scenario parameters, not Vancouver EPDs. The 800,000-sqft floor area is a project-participant published value, not an as-built quantity.",
    }
    (ROOT / "results/vancouver_environment_bridge.json").write_text(
        json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
