import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_block_audit_counts_and_energy_contract():
    result = json.loads(
        (ROOT / "results/vancouver_block_range_audit.json").read_text()
    )
    weekday = result["days"][0]
    assert weekday["all_consecutive_transitions"] == 20_679
    assert weekday["interline_transitions"] == 4_850
    assert weekday["gaps_minutes"]["ge60"] == 3
    assert weekday["interline_gaps_minutes"]["ge60"] == 2
    row = next(
        x for x in weekday["range_scenarios"]
        if x["scenario"] == "40ft" and x["range_km"] == 149
    )
    assert "additional_bus_block_requests" in row
    assert "candidate_block_daily_traction_energy_upper_kwh" in row
    assert "additional_bus_block_requests_fractional" not in row
    assert "battery_kwh_upper_at_source_cold_intensity" not in row
    blocks = pd.read_csv(ROOT / "data/processed/vancouver_blocks_weekday_2023.csv")
    candidates = blocks[~blocks.block_proxy_class.isin(
        {"cap47", "cap70", "cap75", "cap85"}
    )]
    expected = float((candidates.distance_upper_km * 1.79).sum())
    assert abs(expected - row["candidate_block_daily_traction_energy_upper_kwh"]) < 1e-6
