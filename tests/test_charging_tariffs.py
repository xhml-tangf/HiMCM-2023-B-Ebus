from math import isclose

from src.analyze_charging_tariffs import annual_bill, optimize_power


def test_night_energy_requires_grid_capacity_but_no_daytime_billing_peak():
    night = optimize_power(33000, 22, 6, 5000, (6, 22))
    general = optimize_power(33000, 22, 6, 5000, (0, 24))
    assert night["billed_peak_kw"] == 0
    assert isclose(night["physical_peak_kw"], 4125)
    assert isclose(general["billed_peak_kw"], 4125)
    assert optimize_power(33000, 22, 6, 3500, (6, 22))["status"] == "INFEASIBLE_AGGREGATE_WINDOW"


def test_daytime_extension_meets_energy_but_creates_demand_charge():
    night = optimize_power(33000, 20, 6, 3500, (6, 22))
    assert night["nonbilled_available_hours"] == 8
    assert isclose(night["billed_peak_kw"], 2500)
    assert isclose(night["physical_peak_kw"], 3500)
    assert all(p == 0 for p in night["power_kw_by_clock_hour"][6:20])


def test_winter_minimum_is_total_bill_floor_not_a_replacement_for_current_peak():
    bill = annual_bill(0, 0, 0.0614, 12.5, 0.2708, -0.01, prior_11_demand_charges_cad=[1250] * 11)
    assert isclose(bill["annual_bill_cad_after_rider_before_tax"], (11 * 625 + 31 * 0.2708) * 0.99)
    assert bill["months"][-1]["minimum_cad_before_rider"] == 0
    steady = annual_bill(10000, 100, 0.0614, 12.5, 0.2708, -0.01)
    assert steady["annual_minimum_topup_cad"] == 0
    expected = (365 * (10000 * 0.0614 + 0.2708) + 12 * 100 * 12.5) * 0.99
    assert isclose(steady["annual_bill_cad_after_rider_before_tax"], expected)
