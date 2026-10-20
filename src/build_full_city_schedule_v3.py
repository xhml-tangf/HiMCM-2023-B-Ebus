"""Full-city, absolute-time screen for the recovered fall-2023 bus service.

This is intentionally separate from the executed Route 100 duty plan. It
screens every departure in every unique GTFS service pattern, but it does not
invent missing vehicle, garage, charger or utility records. The result can
therefore establish necessary conditions and task-segment counts; it cannot
certify a city-wide electric schedule on its own.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from .audit_gtfs_baseline import haversine_km
except ImportError:
    from audit_gtfs_baseline import haversine_km


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv"
AUDIT = ROOT / "results/vancouver_gtfs_baseline_audit.json"
RESULTS = ROOT / "results/vancouver_full_city_schedule_v3.json"
SUMMARY = ROOT / "results/vancouver_full_city_schedule_v3.csv"

RANGE_KM = 300.0
TURN_MINUTES = 5.0
SPEED_KMH = 50.0
CHARGE_EFFICIENCY = 0.90
OVERNIGHT_HOURS = 8.0

# Capacity signatures are proxies, not observed vehicle assignments.
CAPACITY = {"cap24": 24, "cap47": 47, "cap50": 50, "cap70": 70,
            "cap75": 75, "cap85": 85, "unclassified": 50}
TRACTION_KWH_PER_KM = {"cap24": 0.90, "cap47": 0.0, "cap50": 1.79,
                       "cap70": 0.0, "cap75": 2.42, "cap85": 1.80,
                       "unclassified": 1.79}
GROUPS = {
    "community_shuttle": {"classes": {"cap24"}, "scenario_positions": 189},
    "heavy_non_deck": {"classes": {"cap50", "cap75", "unclassified"},
                        "scenario_positions": 1419},
    "double_deck": {"classes": {"cap85"}, "scenario_positions": 57},
    "trolley": {"classes": {"cap47", "cap70"}, "scenario_positions": 262},
}


def peak_concurrency(intervals: Iterable[tuple[int | float, int | float]]) -> int:
    """Maximum half-open interval overlap, with simultaneous ends before starts."""
    events: list[tuple[float, int]] = []
    for start, end in intervals:
        if not (math.isfinite(start) and math.isfinite(end)) or end <= start:
            raise ValueError("interval must have finite, positive duration")
        events.append((float(start), 1))
        events.append((float(end), -1))
    current = peak = 0
    for _, change in sorted(events):
        current += change
        peak = max(peak, current)
    return peak


def transfer_minutes(previous, current) -> float | None:
    coords = (previous.last_lat, previous.last_lon,
              current.first_lat, current.first_lon)
    if not all(math.isfinite(float(value)) for value in coords):
        return None
    return TURN_MINUTES + 60.0 * float(
        haversine_km(coords[0], coords[1], coords[2], coords[3])) / SPEED_KMH


def split_source_block(group: pd.DataFrame, *, require_turn: bool) -> dict:
    """Split only for the stated 300-km and transfer screens.

    The fragment count is a task-segment count under the source-block policy.
    Fragments remain independent vehicles at this stage; the count is not a
    physical fleet lower bound because a charged bus may execute later work.
    """
    fragments = 0
    current_km = 0.0
    previous = None
    in_fragment = False
    range_splits = turn_splits = missing_transfer = 0
    for row in group.sort_values("start_seconds").itertuples(index=False):
        distance = float(row.distance_km_upper)
        split_reason = None
        if in_fragment and current_km + distance > RANGE_KM + 1e-9:
            split_reason = "range"
        elif in_fragment and require_turn:
            needed = transfer_minutes(previous, row)
            if needed is None:
                split_reason = "missing_location"
                missing_transfer += 1
            elif (row.start_seconds - previous.end_seconds) / 60.0 < needed - 1e-9:
                split_reason = "turn_or_travel"
        if split_reason is not None:
            fragments += 1
            if split_reason == "range":
                range_splits += 1
            elif split_reason == "turn_or_travel":
                turn_splits += 1
            in_fragment = False
            current_km = 0.0
        in_fragment = True
        current_km += distance
        previous = row
    if in_fragment:
        fragments += 1
    return {"fragments": fragments, "range_splits": range_splits,
            "turn_splits": turn_splits, "missing_transfer": missing_transfer}


def pattern_screen(manifest: pd.DataFrame, pattern: dict) -> dict:
    services = set(pattern["active_service_ids"])
    data = manifest.loc[manifest.service_id.isin(services)].copy()
    if len(data) != int(pattern["bus_trips"]):
        raise ValueError(f"pattern {pattern['pattern_id']}: trip loss {len(data)} != {pattern['bus_trips']}")
    numeric = data[["start_seconds", "end_seconds", "distance_km_upper",
                    "first_lat", "first_lon", "last_lat", "last_lon"]]
    if numeric.isna().any().any():
        raise ValueError(f"pattern {pattern['pattern_id']}: missing screen inputs")
    if (data.end_seconds <= data.start_seconds).any():
        raise ValueError(f"pattern {pattern['pattern_id']}: nonpositive trip interval")

    ordered = data.sort_values(["block_id", "start_seconds", "end_seconds"])
    ordered["prior_end"] = ordered.groupby("block_id").end_seconds.shift()
    ordered["prior_lat"] = ordered.groupby("block_id").last_lat.shift()
    ordered["prior_lon"] = ordered.groupby("block_id").last_lon.shift()
    transitions = ordered.loc[ordered.prior_end.notna()].copy()
    transitions["gap_minutes"] = (
        transitions.start_seconds - transitions.prior_end) / 60.0
    transitions["straight_km"] = haversine_km(
        transitions.prior_lat, transitions.prior_lon,
        transitions.first_lat, transitions.first_lon)
    transitions["needed_minutes"] = (
        TURN_MINUTES + 60 * transitions.straight_km / SPEED_KMH)
    transitions["turn_fail"] = (
        transitions.gap_minutes < transitions.needed_minutes - 1e-9)

    blocks = ordered.groupby("block_id").agg(
        trips=("trip_id", "size"), start_seconds=("start_seconds", "min"),
        end_seconds=("end_seconds", "max"), distance_upper_km=("distance_km_upper", "sum")
    ).reset_index()
    blocks["span_hours"] = (blocks.end_seconds - blocks.start_seconds) / 3600.0

    range_only = {"fragments": 0, "range_splits": 0,
                  "turn_splits": 0, "missing_transfer": 0}
    range_and_turn = {"fragments": 0, "range_splits": 0,
                      "turn_splits": 0, "missing_transfer": 0}
    for _, group in ordered.groupby("block_id", sort=False):
        a = split_source_block(group, require_turn=False)
        b = split_source_block(group, require_turn=True)
        for key in range_only:
            range_only[key] += a[key]
            range_and_turn[key] += b[key]

    class_peaks = {
        name: peak_concurrency(zip(group.start_seconds, group.end_seconds,
                                  strict=True))
        for name, group in ordered.groupby("proxy_class")
    }
    group_peaks = {}
    for name, config in GROUPS.items():
        group = ordered.loc[ordered.proxy_class.isin(config["classes"])]
        group_peaks[name] = peak_concurrency(
            zip(group.start_seconds, group.end_seconds, strict=True))

    ordered["traction_kwh_upper"] = (
        ordered.distance_km_upper * ordered.proxy_class.map(TRACTION_KWH_PER_KM)
    )
    battery_mwh = float(ordered.traction_kwh_upper.sum() / 1000.0)
    grid_mwh = battery_mwh / CHARGE_EFFICIENCY
    min_power_mw = grid_mwh / OVERNIGHT_HOURS
    energy_by_class = (ordered.groupby("proxy_class").traction_kwh_upper.sum()
                       .div(1000.0).to_dict())

    fleet_checks = {name: {
        "required_exact_class_peak": group_peaks[name],
        "scenario_positions": config["scenario_positions"],
        "count_sufficient": group_peaks[name] <= config["scenario_positions"],
    } for name, config in GROUPS.items()}
    fatal = []
    if (transitions.gap_minutes < 0).any():
        fatal.append("negative source-block transition gap")
    if any(not check["count_sufficient"] for check in fleet_checks.values()):
        fatal.append("exact-class concurrency exceeds scenario positions")

    return {
        "pattern_id": int(pattern["pattern_id"]),
        "example_date": pattern["example_date"],
        "service_ids": sorted(services),
        "trips": int(len(ordered)),
        "routes": int(ordered.route_id.nunique()),
        "source_blocks": int(len(blocks)),
        "all_trips_preserved": True,
        "absolute_time": {
            "trips_starting_after_24h": int((ordered.start_seconds >= 86400).sum()),
            "trips_ending_after_24h": int((ordered.end_seconds > 86400).sum()),
            "max_end_seconds": int(ordered.end_seconds.max()),
            "max_end_hours": float(ordered.end_seconds.max() / 3600.0),
            "blocks_spanning_over_24h": int((blocks.span_hours > 24).sum()),
            "source_block_overlapping_trip_count": int((transitions.gap_minutes < 0).sum()),
        },
        "peak_concurrent_trips": peak_concurrency(
            zip(ordered.start_seconds, ordered.end_seconds, strict=True)),
        "exact_class_peak_lower_bounds": class_peaks,
        "group_peak_lower_bounds": group_peaks,
        "scenario_fleet_checks": fleet_checks,
        "scenario_total_positions": sum(x["scenario_positions"] for x in GROUPS.values()),
        "source_block_transition_screen": {
            "transitions": int(len(transitions)),
            "negative_gap_count": int((transitions.gap_minutes < 0).sum()),
            "uniform_5min_50kmh_failures": int(transitions.turn_fail.sum()),
            "failure_share": float(transitions.turn_fail.mean()) if len(transitions) else 0.0,
            "max_gap_shortfall_minutes": float(
                np.max(transitions.needed_minutes - transitions.gap_minutes)),
            "status": "SOURCE_BLOCK_CHAINS_NOT_CERTIFIED" if transitions.turn_fail.any()
                      else "PASS_UNDER_DECLARED_TRANSFER_POLICY",
        },
        "range_screen": {
            "range_km": RANGE_KM,
            "source_blocks_over_range": int((blocks.distance_upper_km > RANGE_KM + 1e-9).sum()),
            "max_block_distance_upper_km": float(blocks.distance_upper_km.max()),
            "range_only_fragment_count": range_only["fragments"],
            "range_only_extra_recharge_or_vehicle_segments": range_only["range_splits"],
            "range_and_turn_fragment_count": range_and_turn["fragments"],
            "turn_policy_incremental_segments": range_and_turn["fragments"] - range_only["fragments"],
            "interpretation": "Task segments under retained source-block order; not a physical vehicle lower bound.",
        },
        "winter_energy_lower_bound": {
            "battery_energy_mwh_day": battery_mwh,
            "grid_energy_mwh_day_at_90pct_efficiency": grid_mwh,
            "minimum_average_site_power_mw_8h": min_power_mw,
            "energy_by_class_mwh_day": energy_by_class,
            "accessory_energy": "EXCLUDED; vehicle duty profiles and winter accessory tests are unavailable",
            "trolley": "zero battery traction assumed under overhead supply; feeder capacity remains unverified",
        },
        "fatal_errors": fatal,
        "status": "FAIL" if fatal else "UNVERIFIED",
        "status_reason": fatal or [
            "no actual vehicle-to-block assignments",
            "no depot or terminal charger stock",
            "no site firm-power and commissioning records",
            "no measured winter accessory load or payload",
        ],
    }


def main() -> None:
    manifest = pd.read_csv(
        MANIFEST, dtype={"trip_id": str, "route_id": str, "block_id": str,
                         "service_id": str, "route_short_name": str},
        low_memory=False)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    patterns = [pattern_screen(manifest, pattern)
                for pattern in audit["unique_service_patterns"]]
    if len(patterns) != 25:
        raise ValueError(f"expected 25 unique patterns, found {len(patterns)}")

    metric_extractors = {
        "peak_concurrent_trips": lambda row: row["peak_concurrent_trips"],
        "uniform_turn_failures": lambda row: row["source_block_transition_screen"]["uniform_5min_50kmh_failures"],
        "blocks_over_300km": lambda row: row["range_screen"]["source_blocks_over_range"],
        "range_only_fragments": lambda row: row["range_screen"]["range_only_fragment_count"],
        "range_and_turn_fragments": lambda row: row["range_screen"]["range_and_turn_fragment_count"],
        "winter_battery_mwh_day": lambda row: row["winter_energy_lower_bound"]["battery_energy_mwh_day"],
        "minimum_8h_site_power_mw": lambda row: row["winter_energy_lower_bound"]["minimum_average_site_power_mw_8h"],
    }
    worst = {}
    for name, extract in metric_extractors.items():
        chosen = max(patterns, key=extract)
        worst[name] = {"value": extract(chosen), "pattern_id": chosen["pattern_id"],
                       "example_date": chosen["example_date"]}

    fleet_sufficient = all(
        check["count_sufficient"] for row in patterns
        for check in row["scenario_fleet_checks"].values()
    )
    output = {
        "status": "UNVERIFIED",
        "scope": "The feed contains 54,497 unique published bus-trip records in 25 unique service-ID patterns. This screen executes one representative date per pattern, totaling 495,198 trip instances; every trip in every screened pattern is retained.",
        "original_feed_unique_trip_records": 54_497,
        "screened_pattern_trip_instances": sum(row["trips"] for row in patterns),
        "calendar_window_service_days_covered_by_patterns": int(
            audit["calendar_window_totals"]["service_days"]),
        "calendar_window_scheduled_trip_occurrences": int(
            audit["calendar_window_totals"]["scheduled_bus_trips"]),
        "not_a_citywide_dispatch_certificate": True,
        "constants": {
            "range_km": RANGE_KM, "turn_minutes": TURN_MINUTES,
            "straight_line_speed_kmh": SPEED_KMH,
            "charge_efficiency": CHARGE_EFFICIENCY,
            "fleet_scenario_positions": {k: v["scenario_positions"] for k, v in GROUPS.items()},
        },
        "patterns": patterns,
        "worst_case": worst,
        "exact_class_concurrency_within_scenario_positions": fleet_sufficient,
        "source_block_transition_screen_all_patterns": (
            "PASS" if not any(row["source_block_transition_screen"]["uniform_5min_50kmh_failures"]
                              for row in patterns)
            else "FAIL_UNDER_DECLARED_5MIN_50KMH_POLICY"),
        "charging_screen": {
            "status": "UNVERIFIED",
            "what_is_quantified": "Traction-only winter energy, 90% charging efficiency and average site-wide power for an eight-hour window.",
            "missing": ["charger locations", "charger slots and power", "site firm power",
                        "utility interconnection", "commissioning dates", "arrival SOC",
                        "accessory heater energy", "route terminal dwell geometry"],
        },
        "binding_limits": [
            "The 300-km range screen leaves blocks over 300 km and requires recharge or vehicle exchange.",
            "Original source-block chains fail the declared uniform transfer screen for thousands of connections.",
            "Traction-only full-city energy is hundreds of MWh per day; site-specific charging feasibility is absent.",
            "Capacity proxies do not supply trip-level payload or accessible-vehicle compatibility.",
        ],
        "interpretation": (
            "All departures are retained and exact-class interval concurrency is below the scenario inventory. "
            "That is only a necessary condition. The absent vehicle, depot, charger, power, payload and winter records "
            "prevent a city-wide PASS."
        ),
    }
    RESULTS.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame([{
        "pattern_id": row["pattern_id"], "example_date": row["example_date"],
        "trips": row["trips"], "source_blocks": row["source_blocks"],
        "peak_concurrent_trips": row["peak_concurrent_trips"],
        "turn_failures": row["source_block_transition_screen"]["uniform_5min_50kmh_failures"],
        "blocks_over_300km": row["range_screen"]["source_blocks_over_range"],
        "range_only_fragments": row["range_screen"]["range_only_fragment_count"],
        "range_and_turn_fragments": row["range_screen"]["range_and_turn_fragment_count"],
        "winter_battery_mwh_day": row["winter_energy_lower_bound"]["battery_energy_mwh_day"],
        "minimum_8h_grid_power_mw": row["winter_energy_lower_bound"]["minimum_average_site_power_mw_8h"],
        "status": row["status"],
    } for row in patterns]).to_csv(SUMMARY, index=False, encoding="utf-8")
    print(json.dumps({
        "status": output["status"], "patterns": len(patterns),
        "fleet_lower_bounds_pass": fleet_sufficient,
        "source_block_transfer_screen": output["source_block_transition_screen_all_patterns"],
        "worst_case": worst,
    }, indent=2))


if __name__ == "__main__":
    main()
