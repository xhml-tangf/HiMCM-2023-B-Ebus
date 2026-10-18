"""Service-preserving block diagnostics from the recovered fall-2023 GTFS.

Vehicle classes are route-level proxies from TransLink's 2023 load-factor
capacity diagnostics. They are not an operator vehicle roster. Battery-range
scenarios measure only overnight-charged duty blocks; existing trolleys remain
overhead powered. Missing depot/charger/vehicle registers prevent a certified
city-wide transition score, but the timetable constraints are now real.
"""

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:  # both `python src/...` and `python -m src...` are supported
    from .audit_gtfs_baseline import active_services, haversine_km
except ImportError:
    from audit_gtfs_baseline import active_services, haversine_km

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
RAW = ROOT / "data/raw/vancouver_gtfs_2023"


def norm_route(value: str) -> str:
    text = str(value).strip().upper()
    return str(int(text)) if text.isdigit() else text


def route_classes(proxy: pd.DataFrame, annual: pd.DataFrame) -> dict[str, str]:
    proxy = proxy.loc[proxy.reference_capacity_match.notna()].copy()
    proxy["normalized"] = proxy.route.map(norm_route)
    look = proxy.groupby(["normalized", "capacity_reference_label"]).size().reset_index(name="cells")
    look = look.sort_values(["normalized", "cells"], ascending=[True, False])
    chosen = look.drop_duplicates("normalized").set_index("normalized").capacity_reference_label
    label = {"mini_bus_reference": "cap24",
             "double_deck_like_inferred_not_2018_table": "cap85",
             "articulated_bus_reference": "cap75",
             "articulated_trolley_reference": "cap70",
             "standard_trolley_reference": "cap47",
             "standard_bus_or_highway_coach_reference": "cap50"}
    result = {key: label[value] for key, value in chosen.items()}
    # Annual combined-route cells name every component explicitly. Use those
    # when the independent proxy table does not expose a standalone route.
    by_name = proxy.groupby(proxy.route.astype(str).str.strip()).capacity_reference_label
    for name in annual.route.astype(str):
        for component in re.split(r"[/,]", name):
            component = norm_route(component)
            if component in result:
                continue
            values = [v for key, v in by_name if component in {norm_route(x) for x in re.split(r"[/,]", key)}]
            if values:
                result[component] = label[max(set(values), key=values.count)]
    for route in result:
        if re.fullmatch(r"N?\d+", route) and route.startswith("N"):
            result[route] = result.get(route, "cap50")
    # Capacity labels are not propulsion labels. Preserve the capacity
    # signature and keep powertrain certification separate.
    for route in ("5", "6", "15"):
        result[route] = "cap47"
    return result


def main() -> None:
    started = time.perf_counter()
    manifest = pd.read_csv(PROC / "vancouver_gtfs_trip_manifest_2023.csv",
                           dtype={"trip_id": str, "route_id": str, "block_id": str,
                                  "service_id": str, "route_short_name": str})
    proxy = pd.read_csv(PROC / "vancouver_load_capacity_proxy_2023.csv", dtype={"route": str})
    annual = pd.read_csv(PROC / "vancouver_route_annual_2023.csv", dtype={"route": str})
    calendar = pd.read_csv(RAW / "calendar.txt", dtype=str, keep_default_na=False)
    exceptions = pd.read_csv(RAW / "calendar_dates.txt", dtype=str, keep_default_na=False)
    classes = route_classes(proxy, annual)
    manifest["route_key"] = manifest.route_short_name.map(norm_route)
    manifest["proxy_class"] = manifest.route_key.map(classes).fillna("unclassified")
    # Demand aggregation from the proxy is an approximate class diagnostic.
    manifest.to_csv(PROC / "vancouver_gtfs_trip_manifest_classified_2023.csv", index=False)
    pd.DataFrame([{"route_key": key, "capacity_proxy": value} for key, value in sorted(classes.items())]).to_csv(
        PROC / "vancouver_route_capacity_proxy_2023.csv", index=False)
    manifest["trolley_route_proxy"] = manifest.proxy_class.isin({"cap47", "cap70"})
    dates = {"weekday": "2023-11-14", "saturday": "2023-11-18", "sunday": "2023-11-19", "holiday": "2023-12-25"}
    range_std = [149, 170, 184, 203, 250, 300, 350]
    range_artic = [150, 171, 185, 205, 251, 300, 350]
    days = []
    results = {}
    for kind, day_text in dates.items():
        day = pd.Timestamp(day_text).date()
        services = active_services(calendar, exceptions, day)
        data = manifest.loc[manifest.service_id.isin(services)].copy()
        # If a duty block interlines classes, retain the largest planning class;
        # the block cannot be certified to a smaller vehicle without load data.
        order = {"cap24": 1, "cap85": 2, "cap50": 3, "unclassified": 3,
                 "cap47": 4, "cap75": 5, "cap70": 6}
        data["rank"] = data.proxy_class.map(order)
        transitions = data.sort_values(["block_id", "start_seconds"]).copy()
        transitions["prior_end"] = transitions.groupby("block_id").end_seconds.shift()
        transitions["prior_lat"] = transitions.groupby("block_id").last_lat.shift()
        transitions["prior_lon"] = transitions.groupby("block_id").last_lon.shift()
        transitions["prior_route"] = transitions.groupby("block_id").route_id.shift()
        transitions = transitions.dropna(subset=["prior_end"])
        transitions["gap_minutes"] = (transitions.start_seconds - transitions.prior_end) / 60
        transitions["straight_km"] = haversine_km(transitions.prior_lat, transitions.prior_lon,
                                                   transitions.first_lat, transitions.first_lon)
        dominant = data.sort_values(["block_id", "rank"]).drop_duplicates("block_id", keep="last")
        dominant = dominant[["block_id", "proxy_class", "route_short_name"]].rename(columns={"proxy_class": "block_proxy_class", "route_short_name": "highest_class_route"})
        blocks = data.groupby("block_id").agg(
            trips=("trip_id", "size"), start_seconds=("start_seconds", "min"),
            end_seconds=("end_seconds", "max"), distance_lower_km=("distance_km_lower", "sum"),
            distance_upper_km=("distance_km_upper", "sum"), scheduled_hours=("duration_hours", "sum"),
            n_routes=("route_id", "nunique")).reset_index().merge(dominant, on="block_id", validate="one_to_one")
        blocks["span_hours"] = (blocks.end_seconds - blocks.start_seconds) / 3600
        blocks["kind"] = kind
        blocks.to_csv(PROC / f"vancouver_blocks_{kind}_2023.csv", index=False)
        day_summary = {"date": day_text, "kind": kind, "trips": len(data), "routes": int(data.route_id.nunique()),
                       "published_blocks": len(blocks), "peak_concurrent_trips": None,
                       "block_over_24h": int((blocks.span_hours > 24).sum()),
                       "distance_lower_km": float(blocks.distance_lower_km.sum()),
                       "distance_upper_km": float(blocks.distance_upper_km.sum()), "classes": {}}
        day_summary["interline_blocks"] = int(blocks.n_routes.gt(1).sum())
        day_summary["interline_transitions"] = int(transitions.route_id.ne(transitions.prior_route).sum())
        day_summary["transitions_over_3km_straight_line"] = int(transitions.straight_km.gt(3).sum())
        day_summary["zero_gap_long_transfer"] = int(((transitions.gap_minutes <= 0) &
                                                    (transitions.straight_km > .5)).sum())
        day_summary["gaps_minutes"] = {"ge30": int(transitions.gap_minutes.ge(30).sum()),
                                       "ge40": int(transitions.gap_minutes.ge(40).sum()),
                                       "ge60": int(transitions.gap_minutes.ge(60).sum()),
                                       "ge90": int(transitions.gap_minutes.ge(90).sum())}
        day_summary["peak_concurrent_trips"] = max_count_pairs(data.start_seconds, data.end_seconds)
        for cls, group in blocks.groupby("block_proxy_class"):
            day_summary["classes"][cls] = {"blocks": len(group), "distance_lower_km": float(group.distance_lower_km.sum()),
                                          "distance_upper_km": float(group.distance_upper_km.sum()),
                                          "median_block_km_upper": float(group.distance_upper_km.median()),
                                          "p90_block_km_upper": float(group.distance_upper_km.quantile(.9)),
                                          "max_block_km_upper": float(group.distance_upper_km.max())}
        # Battery candidates exclude existing trolley blocks. Both 40-ft and
        # 60-ft ranges are tested; mini/double-deck are conservatively paired
        # with 40-ft range bands and reported as unvalidated class extensions.
        scenario_rows = []
        for scenario, ranges in [("40ft", range_std), ("60ft", range_artic)]:
            for km in ranges:
                total_blocks = extra = 0
                energy_upper = 0.0
                for row in blocks.itertuples(index=False):
                    if row.block_proxy_class in {"cap47", "cap70"}:
                        continue
                    if row.block_proxy_class == "cap85":
                        continue
                    if scenario == "60ft" and row.block_proxy_class != "cap75":
                        continue
                    if scenario == "40ft" and row.block_proxy_class == "cap75":
                        continue
                    need = math.ceil(row.distance_upper_km / km - 1e-12)
                    total_blocks += 1
                    extra += need - 1
                    # 2020 source: mean 1.60, cold mean 1.79 kWh/km for 40-ft.
                    energy_upper += row.distance_upper_km * (1.79 if scenario == "40ft" else 2.42)
                scenario_rows.append({"scenario": scenario, "range_km": km, "battery_candidate_blocks": total_blocks,
                                      "additional_bus_block_requests_fractional": extra,
                                      "fleet_blocks_after_ceiling": total_blocks + extra,
                                      "replacement_ratio_ceiling": (total_blocks + extra) / total_blocks if total_blocks else None,
                                      "battery_kwh_upper_at_source_cold_intensity": energy_upper})
        day_summary["range_scenarios"] = scenario_rows
        days.append(day_summary)
        results[kind] = blocks
    # Plot winter-range response for the weekday. Replacement counts are block
    # requests under an intentionally conservative upper-distance convention.
    wd = pd.DataFrame(days[0]["range_scenarios"])
    plt.rcParams.update({"font.size": 12, "axes.titlesize": 12, "axes.spines.top": False,
                         "axes.spines.right": False, "font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(6.7, 4.0), constrained_layout=True)
    for scenario, color in [("40ft", "#167a8b"), ("60ft", "#bd5c27")]:
        g = wd[wd.scenario.eq(scenario)]
        ax.plot(g.range_km, 100 * (g.replacement_ratio_ceiling - 1), marker="o", color=color, label=scenario)
    ax.set(xlabel="Reliable range per charge (km)",
           ylabel="Additional block requests (%)",
           title="Fall 2023 weekday service: range stress")
    ax.grid(axis="y", alpha=.2)
    ax.legend(frameon=False)
    fig.savefig(ROOT / "paper/figures/block_range_stress.png", dpi=240)
    plt.close(fig)
    report = {"status": "ACTUAL_PUBLISHED_BLOCKS_RANGE_SCREEN_NOT_CITY_FLEET_CERTIFICATION",
              "source_feed": "TransLink 23SEP_20231020 via pinned public mirror",
              "class_assignment": "route-level proxy from 2023 TSPR capacity clusters; not a 2023 vehicle roster",
              "distance_convention": "upper shape-distance envelope; first stop distance absent in source",
              "bus_range_sources": {"40ft_electric_heat_midlife_km": range_std, "60ft_electric_heat_midlife_km": range_artic,
                                   "source": "TransLink 2020 Appendix C Table C-1; historical vehicle technology, not a 2023 delivered-model specification"},
              "cold_energy_kwh_per_km": {"40ft": 1.79, "60ft": 2.42},
              "unassessed_double_deck_blocks": {kind: int(results[kind].block_proxy_class.eq("cap85").sum())
                                                  for kind in results},
              "days": days,
              "limitations": ["Route-level capacity proxies cannot identify the actual vehicle assigned to a block.",
                              "Battery-bus counts are sequential block requests; depot schedule and reuse can reduce the physical fleet.",
                              "Existing trolley blocks are retained as overhead-electric and not bought again.",
                              "No depot parking, charger, feeder or all-electric candidate payload data are inferred.",
                              "A pass at one representative day does not certify every 2023 service pattern or observed operation.",
                              "Range values assume midlife batteries and 10% duty variability as modeled in 2020; current 2033 vehicles may differ."],
              "computation": {"elapsed_seconds": time.perf_counter() - started}}
    (ROOT / "results/vancouver_block_range_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"days": days, "computation": report["computation"]}, indent=2))


def max_count_pairs(starts, ends):
    events = [(int(x), 1) for x in starts] + [(int(x), -1) for x in ends]
    current = best = 0
    for _, d in sorted(events, key=lambda x: (x[0], x[1])):
        current += d
        best = max(best, current)
    return best


if __name__ == "__main__":
    main()
