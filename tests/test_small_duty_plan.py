from pathlib import Path

import pandas as pd
from src.analyze_vancouver_blocks import transfer_fails


ROOT = Path(__file__).resolve().parents[1]


def test_same_stop_short_turn_is_not_lost_by_clamping_available_time():
    assert transfer_fails(0, 0)
    assert transfer_fails(4, 0)
    assert not transfer_fails(5, 0)
    assert transfer_fails(10, 5)
    assert not transfer_fails(11, 5)


def test_route100_terminal_fragments_respect_daily_range_and_cover_trips():
    manifest = pd.read_csv(
        ROOT / "data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv",
        dtype={"trip_id": str, "block_id": str}, low_memory=False,
    )
    plan = pd.read_csv(ROOT / "data/processed/route100_terminal_duty_plan_2023.csv")
    assert plan.distance_upper_km.max() <= 300.0 + 1e-9
    assert plan.trips.sum() == 223
    assert plan.source_block_id.nunique() == 23
    assert len(plan) == 25
