from dataclasses import replace

from src.model import (Assignment, Charge, Depot, Trip, Vehicle, check_schedule,
                       cost_result, environmental_result, pareto, score)


def fixture():
    trips = [Trip("out", "R", "N", 60, 120, 20, 40, "D", "X", True, ("standard",)),
             Trip("back", "R", "S", 150, 210, 20, 40, "X", "D", True, ("standard",))]
    vehicles = [Vehicle("electric", "D", "standard", 45, 100, 0.9, 80, 1.0, True, True, True, 0.15, 0.0),
                Vehicle("spare", "D", "standard", 45, 100, 0.9, 80, 1.0, True, True, True, 0.15, 0.0)]
    assignments = [Assignment("out", "electric"), Assignment("back", "electric")]
    chargers = [Charge("electric", "D", 240, 300, 50, 0.9)]
    depots = [Depot("D", 1, 50, 50, 2032, 2)]
    matrix = {("D", "D"): 0, ("X", "X"): 0}
    return dict(trips=trips, vehicles=vehicles, assignments=assignments,
                charges=chargers, depots=depots, year=2033,
                peak_capacity_by_route_direction={("R", "N"): 40, ("R", "S"): 40},
                spare_by_depot={"D": 1}, deadhead_minutes=matrix, deadhead_km=matrix)


def test_valid_schedule():
    assert check_schedule(**fixture()).status == "PASS"


def test_missing_city_schedule_is_not_a_pass():
    assert check_schedule(None, None, None, None, None, year=2033).status == "UNVERIFIED"


def test_diesel_heater_fails_all_electric_definition():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], electric_accessories=False)
    result = check_schedule(**args)
    assert result.status == "FAIL"
    assert any("non-electric" in error for error in result.errors)


def test_non_electric_spare_does_not_count_as_full_fleet_conversion():
    args = fixture()
    args["vehicles"][1] = replace(args["vehicles"][1], electric_accessories=False)
    result = check_schedule(**args)
    assert result.status == "FAIL"
    assert any("non-electric 2033 fleet vehicle spare" in e for e in result.errors)


def test_site_and_range_failures():
    args = fixture()
    args["depots"][0] = replace(args["depots"][0], grid_limit_kw=40)
    assert any("grid power" in e for e in check_schedule(**args).errors)
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], kwh_per_km_winter=2.0)
    assert any("minimum SOC" in e for e in check_schedule(**args).errors)


def test_winter_accessory_demand_is_required_and_consumes_energy():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], accessory_kwh_per_hour_winter=None)
    result = check_schedule(**args)
    assert result.status == "UNVERIFIED"
    assert "winter_electric_accessory_demand:electric" in result.missing
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], accessory_kwh_per_hour_winter=12)
    assert any("minimum SOC" in e for e in check_schedule(**args).errors)


def test_in_route_charger_can_be_away_from_home_depot():
    args = fixture()
    args["depots"].append(Depot("X", 1, 50, 50, 2032, 0))
    args["charges"].append(Charge("electric", "X", 125, 145, 30, 0.9))
    assert check_schedule(**args).status == "PASS"


def test_route_vehicle_class_and_capacity_are_hard_constraints():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], vehicle_class="double_decker")
    assert any("incompatible vehicle class" in e for e in check_schedule(**args).errors)
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], capacity=30)
    assert any("capacity shortfall" in e for e in check_schedule(**args).errors)


def test_two_small_buses_can_preserve_one_departure_capacity():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], capacity=25)
    args["vehicles"][1] = replace(args["vehicles"][1], capacity=25)
    args["assignments"] += [Assignment("out", "spare"), Assignment("back", "spare")]
    args["spare_by_depot"] = {"D": 0}
    assert check_schedule(**args).status == "PASS"


def test_spare_can_rotate_after_return_to_depot():
    args = fixture()
    args["trips"].append(Trip("late", "R", "N", 320, 380, 10, 40,
                              "D", "D", True, ("standard",)))
    args["assignments"].append(Assignment("late", "spare"))
    assert check_schedule(**args).status == "PASS"


def test_spare_must_be_at_depot_and_free_during_service():
    args = fixture()
    args["charges"].append(Charge("spare", "D", 70, 110, 50, 0.9))
    args["depots"][0] = replace(args["depots"][0], charger_slots=2,
                                grid_limit_kw=100)
    assert any("spare requirement" in e for e in check_schedule(**args).errors)


def test_duplicate_assignment_cannot_double_count_capacity():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], capacity=25)
    args["assignments"].append(Assignment("out", "electric"))
    result = check_schedule(**args)
    assert any("duplicate assignment" in e for e in result.errors)
    assert any("capacity shortfall" in e for e in result.errors)


def test_empty_manifest_is_unverified():
    args = fixture()
    args["trips"] = []
    args["assignments"] = []
    assert check_schedule(**args).status == "UNVERIFIED"


def test_cost_transfer_and_negative_score():
    base = {2024: 100}
    plan = {2024: 150}
    eligible = {2024: 100}
    zero = cost_result(base, plan, eligible, 0)
    half = cost_result(base, plan, eligible, 0.5)
    assert zero["plan_gross_pv"] == half["plan_gross_pv"]
    assert half["agency_plan_pv"] < zero["agency_plan_pv"]
    assert score(100, 150) == -50


def test_pareto_drops_dominated_point():
    pts = [{"id": "a", "cost": 2, "ghg": 3},
           {"id": "b", "cost": 3, "ghg": 2},
           {"id": "dominated", "cost": 4, "ghg": 4}]
    assert {p["id"] for p in pareto(pts)} == {"a", "b"}


def test_environment_needs_full_lifecycle_boundary():
    assert environmental_result(None, None)["status"] == "UNVERIFIED"
    baseline = {"vehicle_battery_manufacture_t": 10,
                "infrastructure_t": 2, "fuel_supply_combustion_t": 88,
                "electricity_t": 0, "maintenance_t": 0,
                "end_of_life_credit_t": 0, "tailpipe_nox_kg": 100,
                "tailpipe_pm_kg": 5, "electricity_kwh": 0,
                "battery_manufacture_t": 0}
    plan = dict(baseline, fuel_supply_combustion_t=0, electricity_t=20,
                battery_manufacture_t=10, tailpipe_nox_kg=0,
                tailpipe_pm_kg=0, electricity_kwh=1000)
    result = environmental_result(baseline, plan)
    assert result["status"] == "PASS"
    assert result["environment_score_pct"] == 68
    assert result["plan_tailpipe_nox_kg"] == 0
