"""Recover an actual fall-2023 timetable and published vehicle blocks.

The source is TransLink GTFS 23SEP_20231020, preserved in an immutable public
Git mirror. This audit does not infer bus ages, payload or garage assignment
from block numbers. Only route_type=3 fixed-route buses enter the baseline;
HandyDART (715), rail and SeaBus are explicitly excluded.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/vancouver_gtfs_2023"
OUT = ROOT / "data/processed"
REPO = "JaydenCWong/JAAM-project"
COMMIT = "eb584b1108b0d582ae31c7db8e0d7e7b5ba1702b"
PREFIX = "backend/engine/translink_data/"


def time_seconds(values: pd.Series) -> pd.Series:
    """GTFS service-day times may exceed 24:00; never take modulo 24."""
    parts = values.str.split(":", expand=True).astype("int32")
    if parts.shape[1] != 3 or (parts[0] < 0).any() or not parts[1].between(0, 59).all() or not parts[2].between(0, 59).all():
        raise ValueError("invalid GTFS time")
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def haversine_km(lat1, lon1, lat2, lon2):
    a1, a2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2 - lon1)
    term = np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin(dl / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(term, 0, 1)))


def active_services(calendar: pd.DataFrame, exceptions: pd.DataFrame, day: date) -> frozenset[str]:
    label = day.strftime("%Y%m%d")
    weekday = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[day.weekday()]
    selected = set(calendar.loc[(calendar.start_date <= label) & (calendar.end_date >= label)
                                & calendar[weekday].eq("1"), "service_id"])
    for row in exceptions.loc[exceptions.date.eq(label)].itertuples(index=False):
        if row.exception_type == "1":
            selected.add(row.service_id)
        elif row.exception_type == "2":
            selected.discard(row.service_id)
        else:
            raise ValueError("unknown service exception")
    return frozenset(selected)


def peak_concurrency(starts, ends) -> int:
    """Half-open [departure, arrival) intervals, using physical seconds."""
    events = [(int(s), 1) for s in starts] + [(int(e), -1) for e in ends]
    current = peak = 0
    for _, delta in sorted(events):
        current += delta
        peak = max(peak, current)
    return peak


def distance_envelope(start, end, first_known, last_known, shape_start, shape_end):
    """Bound trip distance on a nondecreasing published shape-distance axis.

    Unknown endpoint measures remain unknown: they are bracketed by the shape
    endpoint and nearest known stop measure, not silently declared zero.
    Inputs may be scalars or equal-shaped arrays; output uses their raw unit.
    """
    start_low = np.where(np.isfinite(start), start, shape_start)
    start_high = np.where(np.isfinite(start), start, np.where(np.isfinite(first_known), first_known, shape_end))
    end_low = np.where(np.isfinite(end), end, np.where(np.isfinite(last_known), last_known, shape_start))
    end_high = np.where(np.isfinite(end), end, shape_end)
    lower = np.maximum(0, end_low - start_high)
    upper = end_high - start_low
    if np.any(lower > upper + 1e-8) or np.any(upper < 0):
        raise ValueError("inconsistent shape-distance envelope")
    return lower, upper


def main() -> None:
    started = time.perf_counter()
    read = lambda name: pd.read_csv(RAW / name, dtype=str, keep_default_na=False)
    feed = read("feed_info.txt").iloc[0]
    if (feed.feed_publisher_name != "TransLink" or feed.feed_version != "23SEP_20231020"
            or feed.feed_start_date != "20230904" or feed.feed_end_date != "20231231"):
        raise ValueError("not the pinned fall-2023 TransLink feed")
    routes, trips, stops = read("routes.txt"), read("trips.txt"), read("stops.txt")
    calendar, exceptions = read("calendar.txt"), read("calendar_dates.txt")
    bus_routes = routes.loc[routes.route_type.eq("3")].copy()
    buses = trips.merge(bus_routes[["route_id", "route_short_name", "route_long_name"]], on="route_id", validate="many_to_one")
    if buses.trip_id.duplicated().any() or buses.block_id.eq("").any():
        raise ValueError("duplicate trip IDs or missing published blocks")
    shapes = pd.read_csv(RAW / "shapes.txt", dtype={"shape_id": str})
    shapes.sort_values(["shape_id", "shape_pt_sequence"], inplace=True)
    prev = shapes.groupby("shape_id")[["shape_pt_lat", "shape_pt_lon"]].shift()
    segment_km = haversine_km(prev.shape_pt_lat, prev.shape_pt_lon, shapes.shape_pt_lat, shapes.shape_pt_lon).fillna(0)
    geometric = segment_km.groupby(shapes.shape_id).sum()
    sh_first = shapes.drop_duplicates("shape_id", keep="first").set_index("shape_id")
    sh_last = shapes.drop_duplicates("shape_id", keep="last").set_index("shape_id")
    ratios = (sh_last.shape_dist_traveled - sh_first.shape_dist_traveled) / geometric
    ratio = float(ratios.replace([np.inf, -np.inf], np.nan).dropna().median())
    if 0.98 < ratio < 1.02:
        scale_km, units = 1.0, "km"
    elif 980 < ratio < 1020:
        scale_km, units = 0.001, "m"
    else:
        raise ValueError(f"shape distance unit unverified: raw/geodesic-km ratio {ratio}")
    print(f"Verified distance scale: {units}; median raw/polyline-km ratio {ratio:.6f}", flush=True)
    cols = ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "shape_dist_traveled", "pickup_type", "drop_off_type"]
    st = pd.read_csv(RAW / "stop_times.txt", usecols=cols,
                     dtype={"trip_id": str, "stop_id": str, "arrival_time": str,
                            "departure_time": str, "stop_sequence": "int32", "pickup_type": "int8", "drop_off_type": "int8"})
    raw_stop_time_count = len(st)
    st = st.loc[st.trip_id.isin(set(buses.trip_id))].copy()
    st.sort_values(["trip_id", "stop_sequence"], kind="stable", inplace=True)
    duplicate_sequences = int(st.duplicated(["trip_id", "stop_sequence"]).sum())
    st["arrival_seconds"] = time_seconds(st.arrival_time)
    st["departure_seconds"] = time_seconds(st.departure_time)
    negative_dwell = int((st.departure_seconds < st.arrival_seconds).sum())
    backtime = st.arrival_seconds - st.groupby("trip_id").departure_seconds.shift()
    backwards_between_stops = int((backtime < 0).sum())
    distance_backwards = int((st.dropna(subset=["shape_dist_traveled"]).groupby("trip_id").shape_dist_traveled.diff() < -1e-8).sum())
    if distance_backwards:
        raise ValueError("stop distance axis is not nondecreasing")
    first = st.drop_duplicates("trip_id", keep="first").set_index("trip_id")
    last = st.drop_duplicates("trip_id", keep="last").set_index("trip_id")
    manifest = buses.set_index("trip_id").copy()
    for label, table in [("first", first), ("last", last)]:
        manifest[f"{label}_stop_id"] = table.stop_id
        manifest[f"{label}_shape_distance_raw"] = table.shape_dist_traveled
    manifest["start_seconds"] = first.departure_seconds
    manifest["end_seconds"] = last.arrival_seconds
    manifest["last_departure_seconds"] = last.departure_seconds
    manifest["scheduled_stop_count"] = st.groupby("trip_id").size()
    manifest["has_public_stop"] = ((st.pickup_type != 1) | (st.drop_off_type != 1)).groupby(st.trip_id).any()
    # This feed leaves every first-stop distance blank. Bound the unknown
    # origin by the shape start and earliest known stop measure. This keeps
    # its small distance uncertainty instead of inventing an observed zero.
    coords = stops.set_index("stop_id")[["stop_lat", "stop_lon"]].astype(float)
    known = st.groupby("trip_id").shape_dist_traveled
    lower, upper = distance_envelope(manifest.first_shape_distance_raw.to_numpy(),
        manifest.last_shape_distance_raw.to_numpy(), manifest.index.map(known.first()).to_numpy(dtype=float),
        manifest.index.map(known.last()).to_numpy(dtype=float),
        manifest.shape_id.map(sh_first.shape_dist_traveled).to_numpy(),
        manifest.shape_id.map(sh_last.shape_dist_traveled).to_numpy())
    manifest["distance_km_lower"] = lower * scale_km
    manifest["distance_km_upper"] = upper * scale_km
    manifest["distance_km"] = scale_km * (manifest.last_shape_distance_raw - manifest.first_shape_distance_raw)
    manifest["duration_hours"] = (manifest.end_seconds - manifest.start_seconds) / 3600
    for name in ("first", "last"):
        manifest[f"{name}_lat"] = manifest[f"{name}_stop_id"].map(coords.stop_lat)
        manifest[f"{name}_lon"] = manifest[f"{name}_stop_id"].map(coords.stop_lon)
    missing_trip_times = int(manifest[["start_seconds", "end_seconds"]].isna().any(axis=1).sum())
    nonpositive_durations = int((manifest.duration_hours <= 0).sum())
    negative_distances = int((manifest.distance_km < 0).sum())
    missing_distances = int(manifest.distance_km.isna().sum())
    manifest.reset_index().to_csv(OUT / "vancouver_gtfs_trip_manifest_2023.csv", index=False)
    bus_short_names = set(bus_routes.route_short_name)
    service_patterns: dict[frozenset[str], dict] = {}
    daily_rows = []
    current, end_date = date(2023, 9, 4), date(2023, 12, 31)
    while current <= end_date:
        services = active_services(calendar, exceptions, current)
        if services not in service_patterns:
            day_trips = manifest.loc[manifest.service_id.isin(services)].copy()
            order = day_trips.sort_values(["block_id", "start_seconds", "end_seconds"])
            previous_end = order.groupby("block_id").end_seconds.shift()
            overlap = order.loc[order.start_seconds < previous_end]
            pattern_id = len(service_patterns) + 1
            block = order.groupby("block_id").agg(trips=("service_id", "size"), start_seconds=("start_seconds", "min"),
                      end_seconds=("end_seconds", "max"), distance_km_lower=("distance_km_lower", "sum"),
                      distance_km_upper=("distance_km_upper", "sum"),
                      revenue_hours=("duration_hours", "sum"))
            block["span_hours"] = (block.end_seconds - block.start_seconds) / 3600
            block.reset_index().to_csv(OUT / f"vancouver_gtfs_blocks_2023_pattern_{pattern_id:02d}.csv", index=False)
            service_patterns[services] = {"pattern_id": pattern_id, "example_date": current.isoformat(),
                "active_service_ids": sorted(services), "bus_trips": len(day_trips),
                "bus_routes": day_trips.route_id.nunique(), "published_vehicle_blocks": len(block),
                "peak_concurrent_trips_lower_bound": peak_concurrency(day_trips.start_seconds, day_trips.end_seconds),
                "scheduled_revenue_hours": float(day_trips.duration_hours.sum()),
                "scheduled_trip_km": None if day_trips.distance_km.isna().any() else float(day_trips.distance_km.sum()),
                "scheduled_trip_km_lower": float(day_trips.distance_km_lower.sum()),
                "scheduled_trip_km_upper": float(day_trips.distance_km_upper.sum()),
                "missing_distance_trips": int(day_trips.distance_km.isna().sum()),
                "overlapping_published_block_trip_count": len(overlap),
                "overlap_trip_ids": list(overlap.index.astype(str)),
                "max_block_span_hours": float(block.span_hours.max()),
                "block_span_over_24_hours_count": int((block.span_hours > 24).sum()),
                "max_block_trip_km_upper": float(block.distance_km_upper.max()),
                "median_block_trip_km_upper": float(block.distance_km_upper.median())}
        summary = service_patterns[services]
        daily_rows.append({"date": current.isoformat(), "day_of_week": current.strftime("%A"), **{k:v for k,v in summary.items()
                           if k not in {"active_service_ids", "overlap_trip_ids", "example_date"}}})
        current += timedelta(days=1)
    daily = pd.DataFrame(daily_rows)
    daily.to_csv(OUT / "vancouver_gtfs_daily_service_2023.csv", index=False)
    maximum_trip_day = daily.loc[daily.bus_trips.idxmax()].to_dict()
    maximum_block_day = daily.loc[daily.published_vehicle_blocks.idxmax()].to_dict()
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW.iterdir()) if p.is_file()}
    report = {"status": "HISTORICAL_PUBLISHED_TIMETABLE_RECOVERED_NOT_FULL_FLEET_CERTIFICATION",
              "publisher_as_declared_in_feed": feed.feed_publisher_name, "feed_version": feed.feed_version,
              "source_repository": REPO, "immutable_commit": COMMIT,
              "source_file_urls": {name: f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{PREFIX}{name}" for name in hashes},
              "raw_sha256": hashes, "baseline_service_dates": ["2023-09-04", "2023-12-31"],
              "raw_stop_time_rows": raw_stop_time_count, "bus_stop_time_rows": len(st),
              "bus_route_records": len(bus_routes), "bus_routes_with_trips": manifest.route_id.nunique(),
              "bus_trip_records": len(manifest), "original_block_ids_present_for_every_bus_trip": True,
              "excluded_modes": routes.loc[~routes.route_type.eq("3"), ["route_id", "route_long_name", "route_type"]].to_dict("records"),
              "integrity": {"duplicate_trip_stop_sequences": duplicate_sequences, "negative_stop_dwell_times": negative_dwell,
                            "backwards_time_between_stops": backwards_between_stops, "missing_trip_times": missing_trip_times,
                            "nonpositive_trip_durations": nonpositive_durations, "negative_trip_distances": negative_distances,
                            "missing_exact_trip_distances": missing_distances,
                            "missing_upper_distance_bounds": int(manifest.distance_km_upper.isna().sum()),
                            "backwards_stop_distance_measures": distance_backwards,
                            "shape_distance_unit": units, "median_raw_to_geodesic_km_ratio": ratio,
                            "raw_missing_first_stop_distance": int(manifest.first_shape_distance_raw.isna().sum()),
                            "maximum_trip_distance_interval_width_km": float((manifest.distance_km_upper - manifest.distance_km_lower).max())},
              "unique_service_patterns": list(service_patterns.values()),
              "maximum_trip_day": maximum_trip_day,
              "maximum_published_block_day": maximum_block_day,
              "calendar_window_totals": {"service_days": len(daily), "scheduled_bus_trips": int(daily.bus_trips.sum()),
                                         "scheduled_bus_revenue_hours": float(daily.scheduled_revenue_hours.sum())},
              "limits": ["A scheduled trip is not proof that the trip actually operated.",
                         "This October feed supplies fall/holiday 2023 service, not all January-August timetable versions.",
                         "Published block IDs are vehicle duties, not vehicle identities, bus ages, payloads or garage assignments.",
                         "Fleet size must include spares and non-revenue pull-out/return/charging activities beyond these public trips.",
                         "Missing origin distances yield monotonic shape-distance envelopes; upper bounds may be used for conservative energy tests, not claimed as observed odometer distance.",
                         "Original source data are downloaded for analysis; the mirror does not confer a new license on TransLink data."],
              "computation": {"device": "CPU", "elapsed_seconds": time.perf_counter() - started}}
    (ROOT / "results/vancouver_gtfs_baseline_audit.json").write_text(json.dumps(report, indent=2, default=lambda x: int(x) if isinstance(x, np.integer) else float(x)) + "\n", encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("feed_version", "bus_trip_records", "bus_stop_time_rows", "integrity", "maximum_trip_day", "maximum_published_block_day", "computation")}, indent=2))


if __name__ == "__main__":
    main()
