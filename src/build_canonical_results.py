"""Build the single machine-readable result used by the manuscript.

The canonical interface deliberately separates:
* lifecycle_scores: steady-state 2033 fleet, annualized over asset lives;
* transition: actual 2024--2033 cumulative accounting;
* city_comparison: fleet-level transfer, not route certification.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/research_model"

TECH = {
    "standard": dict(capacity=59, battery_kwh=564.0, traction_kwh_km=1.79, heat_kw=12.0),
    "articulated": dict(capacity=75, battery_kwh=605.0, traction_kwh_km=2.42, heat_kw=18.0),
    "deck": dict(capacity=85, battery_kwh=700.0, traction_kwh_km=1.80, heat_kw=15.0),
    "shuttle": dict(capacity=24, battery_kwh=150.0, traction_kwh_km=0.90, heat_kw=6.0),
}
GLIDER_KG = {"standard": 14_880.0, "articulated": 20_000.0,
             "deck": 18_000.0, "shuttle": 4_500.0}
CONVENTIONAL_GLIDER_KG = {"standard": 11_429.0, "articulated": 16_000.0,
                           "deck": 14_000.0, "shuttle": 4_000.0}
VEHICLE_LIFE = {"standard": 17, "articulated": 17, "deck": 17, "shuttle": 8}
GLIDER_FACTOR = 6.6
BATTERY_FACTOR = 58.0
FACILITY_LIFE = 30
FUEL_CURRENT_LOW_CARBON = 0.302  # kg CO2e per km, 2023 policy mix
GRID_FACTOR = 0.0113              # kg CO2e per kWh
MAINTENANCE_G_PER_KM = 67.5


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _choose_transition() -> Path:
    # central_retrofit is the approved primary facility case. A new canonical
    # run can supersede it without changing this consumer.
    candidates = [
        OUT / "canonical_transition.json",
        OUT / "central_canonical_transition.json",
        OUT / "central_retrofit_transition.json",
        OUT / "central_transition.json",
    ]
    existing = [path for path in candidates if path.exists()]
    # Prefer a transition generated from the approved 15% reserve schedule;
    # older 20% artifacts may remain in the results directory.
    for path in existing:
        try:
            record = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        reserve = str(record.get("reserve", ""))
        reserve_ratio = record.get("reserve_ratio")
        if (reserve_ratio is not None and reserve_ratio >= 0.135) or "15%" in reserve:
            return path
    if existing:
        return existing[0]
    raise FileNotFoundError("no canonical/transition result in results/research_model")


def _choose_schedule(transition: dict) -> Path:
    source = transition.get("source_schedule")
    if source:
        path = OUT / Path(source).name
        if path.exists():
            return path
    path = OUT / "central_schedule.json"
    if not path.exists():
        raise FileNotFoundError("central schedule is missing")
    return path


def _solution_frame(solution: dict) -> pd.DataFrame:
    name = solution.get("ledger_file")
    if not name:
        raise ValueError("solution has no ledger_file")
    path = Path(name)
    if not path.is_absolute():
        path = OUT / path
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _find_baseline(transition: dict, schedule_stem: str,
                   fuel_case: str | None = None) -> pd.DataFrame:
    # The transition JSON does not duplicate its baseline ledger path. Search by
    # the source scenario and fuel case, then fall back to the canonical name.
    fuel = fuel_case or transition.get("fuel_case")
    if fuel is None and transition.get("results"):
        fuel = transition["results"][0].get("fuel_case")
    fuel = fuel or "renewable_mix"
    names = [
        f"{schedule_stem}_{fuel}_baseline_ledger.csv",
        f"central_retrofit_{fuel}_baseline_ledger.csv",
        f"central_{fuel}_baseline_ledger.csv",
    ]
    for name in names:
        path = OUT / name
        if path.exists():
            return pd.read_csv(path)
    raise FileNotFoundError(f"baseline ledger not found; tried {names}")


def _manufacture(cls: str, electric: bool) -> float:
    """Returns kg CO2e per vehicle, including one named battery when EV."""
    mass = GLIDER_KG[cls] if electric else CONVENTIONAL_GLIDER_KG[cls]
    battery = BATTERY_FACTOR * TECH[cls]["battery_kwh"] if electric else 0.0
    return GLIDER_FACTOR * mass + battery


def _stock_by_class(frame: pd.DataFrame, year: int = 2033,
                    electric_only: bool = False) -> dict[str, int]:
    latest = frame.loc[frame.year.eq(year)]
    if latest.empty:
        raise ValueError(f"ledger has no year {year}")
    column = "electric_stock" if electric_only else None
    if column:
        result = latest.groupby("vehicle_class")[column].sum().to_dict()
    else:
        latest = latest.copy()
        latest["stock_total"] = latest["electric_stock"] + latest["conventional_stock"]
        result = latest.groupby("vehicle_class")["stock_total"].sum().to_dict()
    return {str(k): int(round(v)) for k, v in result.items() if v > 0.5}


def _annualized_lifecycle(frame: pd.DataFrame, baseline: pd.DataFrame,
                          common: dict | None = None) -> dict:
    latest = frame.loc[frame.year.eq(2033)]
    base_latest = baseline.loc[baseline.year.eq(2033)]
    if latest.empty or base_latest.empty:
        raise ValueError("2033 ledger missing")
    fleet = _stock_by_class(frame)
    base_fleet = _stock_by_class(baseline)

    plan_manufacture = sum(
        count * _manufacture(cls, True) / (1000 * VEHICLE_LIFE[cls])
        for cls, count in fleet.items() if cls in VEHICLE_LIFE
    )
    base_manufacture = sum(
        count * _manufacture(cls, False) / (1000 * VEHICLE_LIFE[cls])
        for cls, count in base_fleet.items() if cls in VEHICLE_LIFE
    )
    # Infrastructure is charged once in construction and then allocated over
    # its design life. This prevents the last-year zero payment from erasing
    # the asset's embodied carbon from the steady-state score.
    infrastructure = float(frame["infrastructure_t"].sum()) / FACILITY_LIFE
    plan_operation = float(latest["operating_t"].sum())
    base_operation = float(base_latest["operating_t"].sum())
    plan_total = plan_manufacture + infrastructure + plan_operation
    base_total = base_manufacture + base_operation
    if plan_total <= 0 or base_total <= 0:
        raise ValueError("nonpositive environmental denominator")

    plan_km = float(latest["electric_service_km"].sum())
    if plan_km <= 0:
        raise ValueError("no 2033 service km")
    result = {
        "basis": "annualized steady-state 2033 fleet; undiscounted physical emissions",
        "plan_vehicle_manufacturing_t_year": plan_manufacture,
        "baseline_vehicle_manufacturing_t_year": base_manufacture,
        "plan_infrastructure_t_year": infrastructure,
        "plan_operation_t_year": plan_operation,
        "baseline_operation_t_year": base_operation,
        "plan_total_t_year": plan_total,
        "baseline_total_t_year": base_total,
        "plan_gco2e_per_service_km": 1e6 * plan_total / plan_km,
        "baseline_gco2e_per_service_km": 1e6 * base_total / plan_km,
        "environmental_score_pct": 100 * (base_total - plan_total) / base_total,
        "annual_service_km": plan_km,
        "fleet_by_class": fleet,
        "baseline_fleet_by_class": base_fleet,
        "operation_score_2033_pct": 100 * (base_operation - plan_operation) / base_operation,
    }
    if common:
        common_emissions = float(common.get("annual_common_emissions_t", 0.0))
        result["whole_fleet_with_common_trolley"] = {
            "plan_total_t_year": plan_total + common_emissions,
            "baseline_total_t_year": base_total + common_emissions,
            "environmental_score_pct": 100 * (base_total - plan_total) / (base_total + common_emissions),
            "basis": "Adds the same retained trolley activity to both sides.",
        }
    return result


def _common_trolley() -> dict:
    path = OUT / "common_trolley_denominator_bridge.json"
    if not path.exists():
        return {"annual_common_emissions_t": 0.0, "annual_km": None,
                "source": "No common trolley bridge available"}
    bridge = _read_json(path)
    central = bridge.get("central", {})
    km = float(central.get("annual_km", 0.0))
    # 275 retained trolley positions are assumed to consume 2 kWh/km, and the
    # common 262-vehicle renewal is amortized over a 17-year chassis life.
    trolley_mfg = (189 * _manufacture("standard", True)
                   + 73 * _manufacture("articulated", True)) / 17 / 1000
    operation_t = km * (2.0 * GRID_FACTOR + MAINTENANCE_G_PER_KM / 1000) / 1000
    return {
        "annual_km": km,
        "annual_vehicle_manufacturing_t_year": trolley_mfg,
        "annual_common_emissions_t": trolley_mfg + operation_t,
        "source": "Existing 262 common trolley renewal and 275 retained trolley positions; common to both scenarios.",
    }


def _score_solution(solution: dict, baseline: pd.DataFrame, common: dict) -> dict:
    frame = _solution_frame(solution)
    lifecycle = _annualized_lifecycle(frame, baseline, common)
    return {"lifecycle": lifecycle, "frame": frame}


def _select_main(transition: dict, baseline: pd.DataFrame, common: dict) -> dict:
    result = transition["results"][0]
    feasible = [s for s in result["solutions"] if "plan_pv_cad" in s]
    if not feasible:
        raise ValueError("no feasible transition solution")
    scored = []
    for solution in feasible:
        score = _score_solution(solution, baseline, common)["lifecycle"]
        scored.append((solution, score))
    # Approved lexicographic policy: maximize steady-state lifecycle
    # environmental improvement, then minimize discounted transition cost.
    # The tie-break is explicit rather than hidden.
    recommended, recommended_score = min(
        scored,
        key=lambda item: (-item[1]["environmental_score_pct"],
                          item[0].get("plan_pv_cad", math.inf)),
    )
    minimum_cost, minimum_cost_score = min(scored, key=lambda item: item[0]["plan_pv_cad"])
    return {
        "fuel_case": result["fuel_case"],
        "recommended": recommended,
        "minimum_cost": minimum_cost,
        "recommended_lifecycle": recommended_score,
        "minimum_cost_lifecycle": minimum_cost_score,
        "weighted_points": [
            {"weight": s.get("weight"), "plan_pv_cad": s.get("plan_pv_cad"),
             "plan_ghg_t": s.get("plan_ghg_t"),
             "full_life_plan_t": s.get("full_life_plan_t"),
             "full_life_environment_score_pct": s.get("full_life_environment_score_pct"),
             "economic_score_pct": s.get("economic_score_pct"),
             "transition_environment_score_pct": s.get("environmental_score_pct")}
            for s in feasible
        ],
    }


def _schedule_summary(schedule: dict) -> dict:
    electric = schedule["outputs"]["electric"]
    baseline = schedule["outputs"]["baseline"]
    packages = electric["packages"]
    def fleet_of(package: dict) -> int:
        if "fleet_with_15pct_spare" in package:
            return int(package["fleet_with_15pct_spare"])
        if "fleet_with_20pct_spare" in package:
            return int(package["fleet_with_20pct_spare"])
        raise KeyError("package has no reserve-fleet count")

    return {
        "service_patterns": schedule.get("service_patterns"),
        "calendar_days": schedule.get("calendar_days"),
        "pattern_trips_non_trolley": electric.get("pattern_trips"),
        "calendar_trip_instances": electric.get("calendar_trip_instances"),
        "active_buses": electric.get("active_buses"),
        "fleet_with_spares": electric.get("fleet_with_spares"),
        "baseline_active_buses": baseline.get("active_buses"),
        "baseline_fleet_with_spares": baseline.get("fleet_with_spares"),
        "fleet_by_class": {
            cls: sum(fleet_of(p) for p in packages if p["vehicle_class"] == cls)
            for cls in sorted({p["vehicle_class"] for p in packages})
        },
        "firm_power_mw_conservative_sum": sum(float(p["required_power_kw"]) for p in packages) / 1000,
        "annual_grid_gwh": sum(float(p["annual_grid_kwh"]) for p in packages) / 1e6,
        "annual_revenue_km": sum(float(p["annual_revenue_km"]) for p in packages),
        "annual_deadhead_km": sum(float(p["annual_deadhead_km"]) for p in packages),
        "cyclic_vehicle_collision_check": electric.get("cyclic_vehicle_collision_check"),
        "independent_ledger_max_error": electric.get("independent_ledger_max_error"),
    }


def _city_comparison(schedule: dict, lifecycle: dict, main: dict) -> dict:
    comparison = _read_json(ROOT / "results/comparison_city_audit.json")
    three = _read_json(ROOT / "results/three_city_roadmap.json")
    execution = _read_json(ROOT / "results/threecity_execution_certificates_v3.json")
    cta = comparison["chicago_cta"]
    tfl = comparison["london_tfl"]
    v = three["vancouver"]
    c = three["chicago"]
    lo = three["london"]

    def weighted_manufacture(std: int, art: int) -> float:
        return std * _manufacture("standard", True) + art * _manufacture("articulated", True)

    v_classes = lifecycle["fleet_by_class"]
    v_std = sum(v_classes.values())
    vcm = weighted_manufacture(v_std, 0) / 1000
    ccm = weighted_manufacture(1576, 299) / 1000
    lcm = weighted_manufacture(0, 0) / 1000  # overwritten by deck mix below
    lcm = (2445 * _manufacture("standard", True) + 6198 * _manufacture("deck", True)) / 1000
    rows = [
        {
            "city": "Vancouver", "basis": "full-city scheduled plan",
            "fleet_slots": 1725, "existing_electric": 280,
            "conventional_slots": 1445,
            "electric_slots_2033": schedule["outputs"]["electric"]["fleet_with_spares"] + 275,
            "annual_service_km": 106_868_324.0,
            "conversion_fleet_service_km": lifecycle["annual_service_km"],
            "full_life_vehicle_manufacturing_t": vcm,
            "lifecycle_environmental_score_pct": lifecycle["environmental_score_pct"],
            "transition_operating_reduction_pct": lifecycle["operation_score_2033_pct"],
            "peak_or_required_annual_delivery": max(
                (int(x) for x in main["recommended"].get("annual_electric_purchases", [0])),
                default=0),
            "status": "parameterized operational case; common trolley excluded from conversion denominator",
        },
        {
            "city": "Chicago", "basis": "fleet/body case comparison",
            "fleet_slots": c["fleet"], "existing_electric": c["initial_electric"],
            "conventional_slots": c["non_electric"],
            "electric_slots_2033": c["fleet"],
            "annual_service_km": cta["bus_revenue_km"],
            "full_life_vehicle_manufacturing_t": ccm,
            "lifecycle_environmental_score_pct": None,
            "transition_operating_reduction_pct": None,
            "peak_or_required_annual_delivery": c["age_constrained_replacement_model"]["minimum_uniform_annual_capacity_by_life_cap"]["17"],
            "status": "body/age replacement case; no route dispatch certificate",
        },
        {
            "city": "London", "basis": "fleet/body case comparison",
            "fleet_slots": lo["fleet"], "existing_electric": lo["initial_electric"],
            "conventional_slots": lo["non_electric"],
            "electric_slots_2033": lo["fleet"],
            "annual_service_km": None,
            "full_life_vehicle_manufacturing_t": lcm,
            "lifecycle_environmental_score_pct": None,
            "transition_operating_reduction_pct": None,
            "peak_or_required_annual_delivery": lo["peak_annual_renewals"],
            "status": "cohort/body case; annual route km not available in loaded record",
        },
    ]
    return {"method": "common vehicle-size, life, manufacturing and operating parameter model",
            "basis": "fleet/body comparison; Vancouver uniquely receives route-level schedule validation",
            "cities": rows}


def _sensitivity(common: dict) -> list[dict]:
    entries = []
    mapping = {
        "central": "primary_transition",
        "full_new": "full_new_depots",
        "spare10": "ten_percent_reserve",
        "slow_charge": "half_power",
        "winter_stress": "winter_stress",
        "capacity_stress": "capacity_stress",
        "central_high_cost": "high_cost",
    }
    for stem, label in mapping.items():
        path = OUT / f"{stem}_transition.json"
        if not path.exists():
            continue
        transition = _read_json(path)
        reserve = str(transition.get("reserve", ""))
        reserve_ratio = transition.get("reserve_ratio")
        if not ((reserve_ratio is not None and reserve_ratio >= 0.095) or "15%" in reserve):
            # Never mix an older 20% artifact into the canonical sensitivity
            # table. The run can regenerate it after the schedule is current.
            continue
        schedule_path = OUT / Path(transition.get("source_schedule", "central_schedule.json")).name
        power_mw = None
        if schedule_path.exists():
            schedule = _read_json(schedule_path)
            power_mw = sum(float(p["required_power_kw"])
                           for p in schedule["outputs"]["electric"]["packages"]) / 1000
        selected_results = transition["results"] if stem in {"central", "canonical"} else transition["results"][:1]
        for result in selected_results:
            feasible = [s for s in result["solutions"] if "plan_pv_cad" in s]
            if not feasible:
                continue
            recommended = result.get("recommended")
            if recommended is None:
                recommended = max(feasible, key=lambda s: s.get("full_life_environment_score_pct", -math.inf))
            schedule_stem = Path(transition.get("source_schedule", "central_schedule.json")).stem.replace("_schedule", "")
            baseline = _find_baseline(transition, schedule_stem, result["fuel_case"])
            lifecycle = _annualized_lifecycle(_solution_frame(recommended), baseline, common)
            row_label = label
            if stem in {"central", "canonical"} and result["fuel_case"] != "renewable_mix":
                row_label = f"{result['fuel_case']}_baseline"
            entries.append({
                "label": row_label,
                "source": path.name,
                "plan_pv_cad": recommended["plan_pv_cad"],
                "economic_score_pct": recommended["economic_score_pct"],
                "transition_environment_score_pct": recommended["environmental_score_pct"],
                "full_life_environment_score_pct": lifecycle["environmental_score_pct"],
                "full_life_plan_t": lifecycle["plan_total_t_year"],
                "required_power_mw": power_mw,
                "fuel_case": result["fuel_case"],
                "parameter_overrides": transition.get("parameter_overrides", {}),
                "reserve": reserve,
            })
    return entries


def build() -> dict:
    transition_path = _choose_transition()
    transition = _read_json(transition_path)
    schedule = _read_json(_choose_schedule(transition))
    schedule_stem = Path(transition.get("source_schedule", "central_schedule.json")).stem.replace("_schedule", "")
    baseline = _find_baseline(transition, schedule_stem)
    common = _common_trolley()
    main = _select_main(transition, baseline, common)
    lifecycle = main["recommended_lifecycle"]
    schedule_summary = _schedule_summary(schedule)
    sensitivity = _sensitivity(common)
    main_frame = _solution_frame(main["recommended"])
    for row in sensitivity:
        if row["label"] == "primary_transition":
            row["plan_pv_cad"] = main["recommended"]["plan_pv_cad"]
            row["economic_score_pct"] = main["recommended"]["economic_score_pct"]
            row["transition_environment_score_pct"] = main["recommended"]["environmental_score_pct"]
            row["full_life_environment_score_pct"] = lifecycle["environmental_score_pct"]
            row["full_life_plan_t"] = lifecycle["plan_total_t_year"]
        elif row["label"] in {"weighted_mix_baseline", "fossil_diesel_baseline"}:
            fuel = "weighted_mix" if row["label"].startswith("weighted") else "fossil_diesel"
            base = _find_baseline(transition, "central", fuel)
            lc = _annualized_lifecycle(main_frame, base, common)
            row["plan_pv_cad"] = main["recommended"]["plan_pv_cad"]
            row["economic_score_pct"] = main["recommended"]["economic_score_pct"]
            row["full_life_environment_score_pct"] = lc["environmental_score_pct"]
            row["full_life_plan_t"] = lc["plan_total_t_year"]

    result = {
        "status": "CANONICAL_RESEARCH_RESULT",
        "source_transition": transition_path.name,
        "inputs": {
            "source": "results/research_model/input_ledger.json",
            "sha256": _sha(OUT / "input_ledger.json") if (OUT / "input_ledger.json").exists() else None,
            "baseline_fuel": "current low-carbon mix",
            "baseline_intensity_kg_per_km": FUEL_CURRENT_LOW_CARBON,
            "grid_intensity_kg_per_kwh": GRID_FACTOR,
            "vehicle_life_years": VEHICLE_LIFE,
            "facility_life_years": FACILITY_LIFE,
            "reserve_policy": "schedule fleet plus 15% reserve in the canonical policy",
        },
        "schedule": schedule_summary,
        "transition": {
            "source": transition_path.name,
            "recommended": {
                **{k: v for k, v in main["recommended"].items()
                   if k not in {"conversion_years", "grants", "selected"}},
                "conversion_years": main["recommended"].get("conversion_years"),
                "grants": main["recommended"].get("grants"),
            },
            "minimum_cost": {
                **{k: v for k, v in main["minimum_cost"].items()
                   if k not in {"conversion_years", "grants", "selected"}},
                "conversion_years": main["minimum_cost"].get("conversion_years"),
                "grants": main["minimum_cost"].get("grants"),
            },
            "weighted_points": main["weighted_points"],
            "construction": transition.get("construction"),
            "annual_delivery_cap_assumption": transition.get("annual_delivery_cap_assumption"),
        },
        "lifecycle_scores": {
            "recommended": lifecycle["environmental_score_pct"],
            "minimum_cost": main["minimum_cost_lifecycle"]["environmental_score_pct"],
            "recommended_detail": lifecycle,
            "minimum_cost_detail": main["minimum_cost_lifecycle"],
            "transition_boundary": "2024--2033 actual cash/emission ledger; reported separately",
        },
        "city_comparison": _city_comparison(schedule, lifecycle, main),
        "common_trolley": common,
        "sensitivity": sensitivity,
        "verification": {
            "all_non_trolley_pattern_trips_preserved": schedule_summary["pattern_trips_non_trolley"],
            "electric_and_baseline_calendar_match": schedule["outputs"]["electric"]["calendar_trip_instances"] == schedule["outputs"]["baseline"]["calendar_trip_instances"],
            "cyclic_collision": schedule_summary["cyclic_vehicle_collision_check"],
            "independent_ledger_error": schedule_summary["independent_ledger_max_error"],
            "main_mip_gap": main["recommended"].get("mip_gap"),
            "transition_zero_conventional_2033": main["recommended"].get("zero_conventional_2033_check"),
            "method_note": "The schedule is a checked feasible construction; the annual MILP is exact for the selected packages within reported solver tolerance.",
        },
    }
    if result["verification"]["all_non_trolley_pattern_trips_preserved"] != 434_669:
        raise ValueError("non-trolley trip count changed unexpectedly")
    if not result["verification"]["electric_and_baseline_calendar_match"]:
        raise ValueError("electric and baseline calendar counts differ")
    if result["verification"]["cyclic_collision"] != "PASS":
        raise ValueError("cyclic schedule did not pass")
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = build()
    path = OUT / "canonical_v4.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "path": str(path),
        "recommended_lifecycle_environment_pct": result["lifecycle_scores"]["recommended"],
        "minimum_cost_environment_pct": result["lifecycle_scores"]["minimum_cost"],
        "fleet_with_spares": result["schedule"]["fleet_with_spares"],
        "cities": len(result["city_comparison"]["cities"]),
    }, indent=2))


if __name__ == "__main__":
    main()
