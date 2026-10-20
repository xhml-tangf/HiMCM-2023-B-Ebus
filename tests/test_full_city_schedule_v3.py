import json
from pathlib import Path

import pytest

from src.build_full_city_schedule_v3 import peak_concurrency


ROOT = Path(__file__).resolve().parents[1]


def test_peak_concurrency_uses_half_open_intervals():
    assert peak_concurrency([(0, 10), (10, 20)]) == 1
    assert peak_concurrency([(0, 10), (5, 15), (15, 20)]) == 2
    assert peak_concurrency([(0, 1)]) == 1
    with pytest.raises(ValueError):
        peak_concurrency([(1, 1)])


def test_full_city_screen_retains_every_pattern_and_returns_unverified():
    result = json.loads((ROOT / "results/vancouver_full_city_schedule_v3.json").read_text())
    audit = json.loads((ROOT / "results/vancouver_gtfs_baseline_audit.json").read_text())
    assert len(result["patterns"]) == len(audit["unique_service_patterns"]) == 25
    assert all(row["all_trips_preserved"] for row in result["patterns"])
    assert sum(row["trips"] for row in result["patterns"]) == sum(
        row["bus_trips"] for row in audit["unique_service_patterns"])
    assert result["status"] == "UNVERIFIED"
    assert result["not_a_citywide_dispatch_certificate"] is True
    assert result["exact_class_concurrency_within_scenario_positions"] is True
    assert result["charging_screen"]["status"] == "UNVERIFIED"
    assert result["source_block_transition_screen_all_patterns"].startswith("FAIL")


def test_maximum_service_day_quantifies_binding_tasks_without_claiming_vehicle_bound():
    result = json.loads((ROOT / "results/vancouver_full_city_schedule_v3.json").read_text())
    row = next(x for x in result["patterns"] if x["example_date"] == "2023-10-13")
    assert row["trips"] == 22_494
    assert row["source_blocks"] == 1_756
    assert row["peak_concurrent_trips"] == 1_089
    assert row["source_block_transition_screen"]["uniform_5min_50kmh_failures"] == 4_606
    assert row["range_screen"]["source_blocks_over_range"] == 265
    assert row["range_screen"]["max_block_distance_upper_km"] == pytest.approx(745.3279)
    assert row["range_screen"]["range_only_fragment_count"] == 2_032
    assert row["range_screen"]["range_and_turn_fragment_count"] == 6_486
    assert row["winter_energy_lower_bound"]["battery_energy_mwh_day"] == pytest.approx(469.208098713)
    assert "not a physical vehicle lower bound" in row["range_screen"]["interpretation"].lower()
    assert row["absolute_time"]["max_end_hours"] > 24
