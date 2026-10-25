"""Small adversarial checks; these numbers are synthetic, not field evidence."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from trial_naive_linked_routes import Trip, assign_at_limit, inventory_bound, solve, validate, parse_gtfs_time


def make(rows):
    return [Trip(str(i), route, start, end, a, b, km)
            for i, (route, start, end, a, b, km) in enumerate(rows)]


def test_distinct_terminals_cannot_teleport():
    t = make([("x", 0, 300, "A", "B", 10), ("x", 600, 900, "C", "D", 10)])
    assert solve(t, gap=0)["fleet_size"] == 2


def test_simultaneous_arrival_and_departure_respects_turnaround():
    t = make([("x", 0, 300, "A", "B", 10), ("x", 300, 600, "B", "A", 10)])
    assert solve(t, gap=0)["fleet_size"] == 1
    assert solve(t, gap=1)["fleet_size"] == 2


def test_range_can_make_inventory_bound_insufficient():
    t = make([("x", 0, 300, "A", "B", 60), ("x", 600, 900, "B", "A", 60)])
    assert inventory_bound(t)[0] == 1
    result = solve(t, range_km=100)
    assert result["fleet_size"] == 2 and result["proof"] == "exhausted_smaller_fleets"
    assert result["searches"][0]["exhaustive"]
    validate(t, result)


def test_interlining_changes_fleet_without_changing_service():
    t = make([("x", 0, 300, "A", "B", 10), ("y", 600, 900, "B", "A", 10)])
    assert solve(t)["fleet_size"] == 1
    assert solve(t, separate=True)["fleet_size"] == 2


def test_long_trip_is_infeasible_and_limit_is_not_infeasibility():
    t = make([("x", 0, 300, "A", "B", 151)])
    assert solve(t)["status"] == "INFEASIBLE"
    limited = assign_at_limit(t, 1, node_limit=0)
    assert limited["interrupted"] and not limited["exhaustive"]


def test_absolute_time_cross_midnight_is_not_reset():
    assert parse_gtfs_time(" 6:02:00") == 21720
    assert parse_gtfs_time("25:00:00") == 90000
    t = make([("x", 86300, 86700, "A", "B", 10), ("x", 86500, 87000, "B", "A", 10)])
    assert solve(t, gap=0)["fleet_size"] == 2


def test_complete_enumeration_not_bus_label_permutations():
    t = make([("x", 0, 300, "A", "B", 10), ("x", 0, 300, "A", "B", 10),
              ("x", 600, 900, "B", "A", 10)])
    result = assign_at_limit(t, 2, enumerate_all=True)
    assert result["exhaustive"] and result["complete_covers"] == 2
