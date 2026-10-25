"""Audit CTA 2023 vehicle-age and fuel-energy rows from the DOT public API."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MILES_TO_KM = 1.609344
US_GALLON_TO_LITRES = 3.785411784


def age_due_bounds(rows: list[dict], life: int) -> dict[str, int]:
    return {
        "definitely_age_due_slots": sum(row["vehicles"] for row in rows
                                        if row["age_low"] + 1 >= life),
        "possibly_age_due_slots": sum(row["vehicles"] for row in rows
                                      if (row["age_high"] if row["age_high"] is not None
                                          else 999) + 1 >= life),
    }


def calculate() -> dict:
    raw = json.loads((ROOT / "materials/sources/raw/cta_2023_age_distribution.json").read_text(
        encoding="utf-8"))
    vehicle_rows = [r for r in raw if r["vehicle_type"] in ("Bus", "Articulated Bus")]
    assert len(vehicle_rows) == 2
    bins = [(f"_{age}", age, age) for age in range(13)] + [
        ("_13_15", 13, 15), ("_16_20", 16, 20), ("_21_25", 21, 25),
        ("_26_30", 26, 30), ("_31_60", 31, 60), ("_60", 61, None)]
    cleaned = []
    for row in vehicle_rows:
        assert row["ntd_id"] == "50066" and row["report_year"] == "2023"
        assert sum(int(row[key]) for key, _, _ in bins) == int(row["total_vehicles"])
        for key, low, high in bins:
            count = int(row[key])
            if count:
                cleaned.append({"vehicle_type": row["vehicle_type"], "age_low": low,
                                "age_high": high, "vehicles": count})
    with (ROOT / "data/processed/cta_2023_age_cohorts.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cleaned[0]))
        writer.writeheader()
        writer.writerows(cleaned)
    fleet = sum(int(row["total_vehicles"]) for row in vehicle_rows)
    age = sum(float(row["average_age_of_fleet_in_years"]) * int(row["total_vehicles"])
              for row in vehicle_rows) / fleet
    assert fleet == 1875 and round(age, 1) == 11.2
    energy = json.loads((ROOT / "materials/sources/raw/cta_2023_fuel_energy.json").read_text(
        encoding="utf-8"))
    bus = next(row for row in energy if row["modecd"] == "MB" and row["typeofservicecd"] == "DO")
    diesel_gallons = float(bus["diesel_gal"])
    diesel_miles = float(bus["diesel"])
    electricity = float(bus["electric_battery_kwh"])
    electric_miles = float(bus["electric_battery"])
    source_miles = diesel_miles + electric_miles
    profile_revenue_miles = 45_411_226
    output = {
        "status": "OBSERVED_AGE_STOCK_AND_MATCHED_ENERGY_ROWS_SCOPE_CHECK_REQUIRED",
        "age_source": "https://data.transportation.gov/d/6abt-uhgq",
        "energy_source": "https://data.transportation.gov/d/8ehq-7his",
        "filter": "NTD ID 50066; Report Year 2023; Bus and Articulated Bus only",
        "year_end_bus_inventory": fleet,
        "standard_bus_inventory": 1576,
        "articulated_bus_inventory": 299,
        "weighted_average_age_years": age,
        "age_13_or_older_buses": sum(r["vehicles"] for r in cleaned if r["age_low"] >= 13),
        "age_16_or_older_buses": sum(r["vehicles"] for r in cleaned if r["age_low"] >= 16),
        "conditional_2024_renewal_bounds_by_chassis_life_cap": {
            life: age_due_bounds(cleaned, life) for life in (12, 14, 17)
        },
        "profile_vehicles_available_for_maximum_service": 1895,
        "profile_available_minus_year_end_inventory": 1895 - fleet,
        "diesel_gallons_2023": diesel_gallons,
        "diesel_litres_2023": diesel_gallons * US_GALLON_TO_LITRES,
        "battery_charging_electricity_kwh_2023": electricity,
        "matched_diesel_miles": diesel_miles,
        "matched_battery_bus_miles": electric_miles,
        "diesel_litres_per_matched_km": diesel_gallons * US_GALLON_TO_LITRES / (diesel_miles * MILES_TO_KM),
        "charging_kwh_per_matched_battery_bus_km": electricity / (electric_miles * MILES_TO_KM),
        "sum_fuel_table_bus_miles": source_miles,
        "profile_revenue_miles": profile_revenue_miles,
        "fuel_table_miles_share_of_profile_revenue_miles": source_miles / profile_revenue_miles,
        "warning": "The year-end inventory (1875) and VAMS (1895) are distinct reported measures; do not add or silently reconcile them. Fuel-table mileage is smaller than the agency profile's revenue mileage, so its energy intensities are matched-table diagnostics only until scopes are resolved. These are annual fleet averages, not winter-peak guarantees or full life-cycle factors.",
    }
    (ROOT / "results/cta_2023_detail_audit.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(json.dumps(calculate(), indent=2))
