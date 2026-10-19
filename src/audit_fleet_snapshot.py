"""Reconcile the 2022/2023 bridge and 2025 CMBC fleet snapshot."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = pd.read_csv(ROOT / "data/processed/translink_fleet_bridge_2023_2025.csv")
    get = lambda snap, metric: int(data.query("snapshot == @snap and metric == @metric").value.iloc[0])
    classes_2025 = {k: get(2025, k) for k in ("trolley", "battery", "hybrid", "cng", "diesel", "gasoline_shuttle")}
    assert sum(classes_2025.values()) == get(2025, "active_total") == 1733
    years = {row.metric.removeprefix("built_"): int(row.value)
             for row in data.query("snapshot == 2025").itertuples() if row.metric.startswith("built_")}
    assert sum(years.values()) == 1733
    ages = {}
    for year, count in years.items():
        age = 2025 - int(year)
        band = "0-4" if age <= 4 else "5-9" if age <= 9 else "10-14" if age <= 14 else "15-19" if age <= 19 else "20+"
        ages[band] = ages.get(band, 0) + count
    assert ages == {"0-4": 392, "5-9": 543, "10-14": 91, "15-19": 705, "20+": 2}
    classes_2022 = {k: get(2022, k) for k in ("hybrid", "low_emission_diesel", "cng", "trolley", "battery",
                                                 "contracted_diesel_hybrid", "gasoline_shuttle")}
    assert sum(classes_2022.values()) == get(2022, "total") == 1711
    assert get(2023, "battery_scenario") == get(2023, "zero_emission_total") - get(2023, "trolley")
    output = {
        "status": "CROSS_YEAR_SCENARIO_NOT_VERIFIED_2023_BOUNDS",
        "snapshot_2025_date": "2025-11-18",
        "classes_2025": classes_2025,
        "age_bands_2025": ages,
        "young_0_to_4": ages["0-4"],
        "remaining_non_electric_or_non_trolley_2025": classes_2025["hybrid"] + classes_2025["cng"]
            + classes_2025["diesel"] + classes_2025["gasoline_shuttle"],
        "built_2023_2025": years["2023"] + years["2024"] + years["2025"],
        "fleet_2023_categories": classes_2022,
        "fleet_2023_total_estimate": get(2023, "total"),
        "fleet_2023_interval": [get(2023, "total_low"), get(2023, "total_high")],
        "warnings": ["2023 total and retained BEBs are scenario parameters; cross-date subtraction is not evidence of deliveries or stock bounds.",
                     "2025 snapshot includes active vehicles only; 63 in-storage vehicles are separate.",
                     "Vehicle specific status, training/heritage colors and exact 2033 model specifications need review."]}
    (ROOT / "results/fleet_scale_audit.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
