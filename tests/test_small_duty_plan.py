from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


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
