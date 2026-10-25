"""Audit the 2023 TransLink route data without inventing a trip timetable."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "materials" / "sources" / "raw"
PROCESSED = ROOT / "data" / "processed"


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    annual = pd.read_csv(RAW / "translink_tspr_2023_annual.csv", low_memory=False)
    service = pd.read_csv(RAW / "translink_tspr_2023_hourly.csv", low_memory=False)
    load = pd.read_csv(RAW / "translink_tspr_2023_peakload.csv", low_memory=False)

    annual = annual.loc[annual["CalendarYear"].eq(2023)].copy()
    service = service.loc[service["SeasonYear"].eq(2023)].copy()
    load = load.loc[load["SeasonYear"].eq(2023)].copy()
    for table in (annual, service, load):
        table["route"] = table["Lineno_renamed"].astype(str).str.strip()

    # These are published time-range values, not exact one-hour trip records.
    # The source has no vehicle/block IDs, so a full vehicle schedule cannot
    # be reconstructed from this table alone.
    annual.rename(columns={"Annual_Service_Hours": "service_hours_2023",
                           "Annual_Revenue_Hours": "revenue_hours_2023",
                           "AVG_speed_km_per_hr": "average_speed_kmh_2023"}, inplace=True)
    annual[["route", "service_hours_2023", "revenue_hours_2023",
            "average_speed_kmh_2023", "Average_Peak_Passenger_Load",
            "Average_Peak_Load_Factor"]].to_csv(
        PROCESSED / "vancouver_route_annual_2023.csv", index=False)

    service.rename(columns={"Hour_Range": "time_range_code",
                            "Average_Trips_Per_Clock_Hour_Per_Direction":
                            "average_trips_per_clock_hour_per_direction"}, inplace=True)
    service[["route", "DayType", "Season", "time_range_code",
             "average_trips_per_clock_hour_per_direction",
             "Annual_Revenue_Hours", "Annual_Service_Hours"]].to_csv(
        PROCESSED / "vancouver_route_time_service_2023.csv", index=False)

    load.rename(columns={"HourRange": "time_range_code",
                         "direction_updated": "direction",
                         "Average_Peak_Passenger_Load": "average_peak_passengers",
                         "Average_Peak_Load_Factor": "average_peak_load_factor_pct"}, inplace=True)
    load[["route", "DayType", "Season", "time_range_code", "direction",
          "average_peak_passengers", "average_peak_load_factor_pct"]].to_csv(
        PROCESSED / "vancouver_route_time_load_2023.csv", index=False)

    # The statutory report gives these published values, in thousands of
    # service hours: 4,753 conventional bus + 706 shuttle + 118 West Vancouver.
    # This comparison is an audit, not a correction factor.
    statutory_service_hours = (4753 + 706 + 118) * 1000
    csv_service_hours = annual["service_hours_2023"].sum()
    coverage = csv_service_hours / statutory_service_hours
    possible_route_time = service[
        "average_trips_per_clock_hour_per_direction"].notna().sum()
    possible_load = load["average_peak_passengers"].notna().sum()
    audit = {
        "baseline_year": 2023,
        "annual_route_count": int(annual["route"].nunique()),
        "route_time_service_records": int(len(service)),
        "route_time_service_records_with_frequency": int(possible_route_time),
        "route_time_direction_load_records": int(len(load)),
        "route_time_direction_load_records_with_load": int(possible_load),
        "time_range_codes": sorted(int(x) for x in service["time_range_code"].dropna().unique()),
        "csv_annual_service_hours": round(float(csv_service_hours), 1),
        "statutory_annual_service_hours": statutory_service_hours,
        "csv_to_statutory_service_hours_ratio": round(float(coverage), 5),
        "source_limitations": [
            "The public CSV excludes discontinued bus routes.",
            "Time-range mean frequency is not an exact departure timetable.",
            "Peak load is an average of peak loads, not the maximum observed load.",
            "No vehicle assignment, block, depot, state of charge, or 2023 fleet-age registry is in the CSV.",
            "The report's total conventional transit includes other modes; the audit denominator uses only three bus categories.",
        ],
    }
    (PROCESSED / "vancouver_data_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
