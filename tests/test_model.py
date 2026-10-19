from dataclasses import replace

import pytest

from src.model import (Assignment, Charge, DailySchedule, Depot, FuelSystem, OverheadFeeder, Trip, Vehicle,
                       check_periodic_schedule, check_schedule, cost_result, environmental_result,
                       pareto, score)


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


def periodic_counterexample(charges=None):
    trip = Trip("daily", "R", "N", 60, 180, 60, 40, "D", "D",
                True, ("standard",))
    bus = Vehicle("electric", "D", "standard", 45, 100, 1.0, 100, 1.0,
                  True, True, True, 0.1, 0.0)
    depot = Depot("D", 0 if not charges else 1, 0 if not charges else 100,
                  0 if not charges else 100, 2032, 1)
    day = DailySchedule([trip], [Assignment("daily", "electric")], charges or [],
                        {("R", "N"): 40}, {"D": 0})
    matrix = {("D", "D"): 0}
    return ([day, day], [bus], [depot],
            {"year": 2033, "deadhead_minutes": matrix, "deadhead_km": matrix})


def test_single_day_pass_cannot_reset_soc_for_a_repeating_service():
    days, vehicles, depots, options = periodic_counterexample()
    single = check_schedule(
        days[0].trips, vehicles, days[0].assignments, days[0].charges, depots,
        peak_capacity_by_route_direction=days[0].peak_capacity_by_route_direction,
        spare_by_depot=days[0].spare_by_depot, **options)
    assert single.status == "PASS"
    assert single.metrics["final_energy_kwh:electric"] == pytest.approx(40)

    periodic = check_periodic_schedule(days, vehicles, depots, **options)
    assert periodic.status == "FAIL"
    assert any("day 2: minimum SOC violated" in error for error in periodic.errors)
    assert any("periodic SOC closure violated" in error for error in periodic.errors)


def test_periodic_service_accepts_post_service_depot_charge():
    charge = Charge("electric", "D", 180, 220, 100, 0.9)
    days, vehicles, depots, options = periodic_counterexample([charge])
    result = check_periodic_schedule(days, vehicles, depots, **options)
    assert result.status == "PASS"
    assert result.metrics["final_energy_kwh:electric:1"] == pytest.approx(100)
    assert result.metrics["initial_energy_kwh:electric:2"] == pytest.approx(100)
    assert result.metrics["cycle_end_energy_kwh:electric"] == pytest.approx(100)


def test_charge_energy_power_and_station_relation_is_explicit():
    trip = Trip("dummy", "R", "N", 60, 120, 0, 40, "D", "D",
                True, ("standard",))
    bus = Vehicle("electric", "D", "standard", 45, 100, 0.9, 20, 0.0,
                  True, True, True, 0.1, 0.0)
    depot = Depot("D", 1, 10, 10, 2032, 1)
    args = dict(trips=[trip], vehicles=[bus],
                assignments=[Assignment("dummy", "electric")],
                charges=[Charge("electric", "D", 120, 180, 10, 0.9)],
                depots=[depot], year=2033,
                peak_capacity_by_route_direction={("R", "N"): 40},
                spare_by_depot={"D": 0},
                deadhead_minutes={("D", "D"): 0},
                deadhead_km={("D", "D"): 0})
    result = check_schedule(**args)
    assert result.status == "PASS"
    assert result.metrics["charge_grid_kwh:electric"] == pytest.approx(10)
    assert result.metrics["charge_accepted_kwh:electric"] == pytest.approx(9)
    assert result.metrics["final_energy_kwh:electric"] == pytest.approx(29)
    assert result.metrics["final_energy_kwh:electric"] == pytest.approx(
        bus.initial_kwh - result.metrics["traction_kwh:electric"]
        - result.metrics["auxiliary_kwh:electric"]
        + result.metrics["charge_accepted_kwh:electric"])


def test_charge_power_cannot_exceed_charger_or_bypass_station_slot():
    args = fixture()
    args["charges"][0] = replace(args["charges"][0], power_kw=60)
    result = check_schedule(**args)
    assert any("Pmax*u" in error for error in result.errors)

    args = fixture()
    args["depots"][0] = replace(args["depots"][0], charger_slots=0)
    result = check_schedule(**args)
    assert any("without an available station slot" in error for error in result.errors)


def test_station_occupancy_and_one_site_per_vehicle_are_checked():
    args = fixture()
    args["spare_by_depot"] = {"D": 0}
    args["charges"].append(Charge("spare", "D", 250, 260, 20, 0.9))
    args["depots"][0] = replace(args["depots"][0], grid_limit_kw=100)
    result = check_schedule(**args)
    assert any("charger slots exceeded" in error for error in result.errors)

    args = fixture()
    args["depots"].append(Depot("X", 1, 50, 50, 2032, 0))
    args["charges"].append(Charge("electric", "X", 250, 300, 20, 0.9))
    result = check_schedule(**args)
    assert any("simultaneous charging sessions" in error for error in result.errors)


def fuel_fixture():
    args = fixture()
    args["year"] = 2023
    args["charges"] = []
    args["vehicles"] = [replace(bus, battery_kwh=0, initial_kwh=0,
                                electric_propulsion=False, electric_accessories=False,
                                accessory_kwh_per_hour_winter=None, energy_source="fuel",
                                fuel=FuelSystem("L", 200, 100, 20, 0.6, 2))
                        for bus in args["vehicles"]]
    return args


def test_conventional_baseline_uses_fuel_instead_of_fictitious_battery():
    args = fuel_fixture()
    assert check_schedule(**args).status == "PASS"
    args["vehicles"][0] = replace(args["vehicles"][0], fuel=FuelSystem("L", 200, 45, 20, 0.6, 2))
    # 40 km uses 24 L and the 2.5-hour duty uses another 5 L.
    assert any("fuel reserve" in e for e in check_schedule(**args).errors)
    args["vehicles"][0] = replace(args["vehicles"][0], fuel=None)
    assert "winter_fuel_budget:electric" in check_schedule(**args).missing


def test_fuel_vehicle_cannot_satisfy_strict_2033_fleet():
    args = fuel_fixture()
    args["year"] = 2033
    assert any("non-electric 2033" in e for e in check_schedule(**args).errors)


def trolley_fixture():
    args = fixture()
    args["charges"] = []
    args["vehicles"] = [replace(bus, battery_kwh=0, initial_kwh=0,
                                energy_source="overhead", overhead_peak_kw=200)
                        for bus in args["vehicles"]]
    args["overhead_paths"] = {("trip", "out"): ("F",), ("trip", "back"): ("F",)}
    args["overhead_feeders"] = [OverheadFeeder("F", 300, 2023)]
    return args


def test_trolley_requires_wired_path_and_feeder_not_a_battery():
    args = trolley_fixture()
    assert check_schedule(**args).status == "PASS"
    args["overhead_paths"].pop(("trip", "back"))
    result = check_schedule(**args)
    assert result.status == "UNVERIFIED"
    assert "wired_path:trip:back" in result.missing
    args = trolley_fixture()
    args["overhead_feeders"] = []
    assert "overhead_feeder:F" in check_schedule(**args).missing


def test_trolley_concurrent_feeder_power_and_stationary_heating():
    args = trolley_fixture()
    args["assignments"] += [Assignment("out", "spare"), Assignment("back", "spare")]
    args["spare_by_depot"] = {"D": 0}
    assert any("overhead feeder power exceeded" in e for e in check_schedule(**args).errors)
    args = trolley_fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], accessory_kwh_per_hour_winter=10)
    assert "wired_path:location:X" in check_schedule(**args).missing
    args["overhead_paths"][("location", "X")] = ("F",)
    assert check_schedule(**args).status == "PASS"


def test_arrival_below_reserve_cannot_be_hidden_by_subsequent_charge():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], initial_kwh=65)
    args["charges"][0] = replace(args["charges"][0], depot="X")
    args["depots"].append(Depot("X", 1, 50, 50, 2032, 0))
    args["deadhead_minutes"].update({("D", "X"): 10, ("X", "D"): 10})
    args["deadhead_km"] = {("D", "D"): 0, ("X", "X"): 0,
                           ("D", "X"): 11, ("X", "D"): 11}
    result = check_schedule(**args)
    assert any("minimum SOC" in e and "240" in e for e in result.errors)


def test_deadheading_vehicle_does_not_count_as_a_depot_spare():
    args = fixture()
    args["trips"] = [Trip("out", "R", "N", 60, 120, 20, 40, "X", "D", True, ("standard",)),
                     Trip("other", "R", "S", 40, 55, 5, 40, "D", "D", True, ("standard",))]
    args["assignments"] = [Assignment("out", "electric"), Assignment("other", "spare")]
    args["charges"] = []
    args["deadhead_minutes"] = {("D", "X"): 10, ("D", "D"): 0}
    args["deadhead_km"] = {("D", "X"): 2, ("D", "D"): 0}
    # At 50--55 one bus is driving to X and the other is still in service.
    assert any("spare requirement" in e and "50" in e for e in check_schedule(**args).errors)


def test_returned_vehicle_counts_as_spare_only_after_driving_back():
    args = fixture()
    args["trips"] = [args["trips"][0],
                     Trip("other", "R", "S", 135, 150, 5, 40, "D", "D", True, ("standard",))]
    args["assignments"] = [Assignment("out", "electric"), Assignment("other", "spare")]
    args["charges"] = []
    args["deadhead_minutes"] = {("D", "D"): 0, ("X", "D"): 10}
    args["deadhead_km"] = {("D", "D"): 0, ("X", "D"): 2}
    assert check_schedule(**args).status == "PASS"
    args["trips"][1] = replace(args["trips"][1], start_min=125)
    assert any("spare requirement" in e and "125" in e for e in check_schedule(**args).errors)


def test_invalid_energy_and_trip_inputs_cannot_pass():
    args = fixture()
    args["vehicles"][0] = replace(args["vehicles"][0], usable_fraction=1.1)
    assert any("invalid battery" in e for e in check_schedule(**args).errors)
    args = fixture()
    args["trips"][0] = replace(args["trips"][0], distance_km=-20)
    assert any("invalid trip" in e for e in check_schedule(**args).errors)


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
