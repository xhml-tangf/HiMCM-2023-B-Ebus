"""CPU LP bounds for charging, using the actual April 2023 BC Hydro tariff.

These are aggregate relaxations: all requested energy must fit a declared
charging window and site power. They do not certify individual vehicle,
charger-slot, winter or route feasibility. Historical 40-ft annual energy
intensities are sensitivity inputs, not measured 2023 depot-bus consumption.
"""

from __future__ import annotations

import calendar
import csv
import json
import math
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]


def optimize_power(daily_grid_kwh: float, arrival_hour: int, departure_hour: int,
                   site_kw: float, demand_hours: tuple[int, int]) -> dict:
    """Continuous 1-hour charging, common window which may cross midnight.

    Minimizes tariff-billed peak, then physical peak at that optimal billed
    peak. Common endpoints and constant rates make the 1-hour representation
    exact for this relaxation. A cumulative-energy bound independently checks
    the LP. No integer charger-slot count is inferred from aggregate power.
    """
    if not (daily_grid_kwh > 0 and site_kw > 0 and
            0 <= departure_hour < 24 and 0 <= arrival_hour < 24 and arrival_hour != departure_hour and
            0 <= demand_hours[0] < demand_hours[1] <= 24):
        raise ValueError("invalid energy, power or overnight window")
    available = np.array([(h >= arrival_hour or h < departure_hour) if arrival_hour > departure_hour
                          else (arrival_hour <= h < departure_hour) for h in range(24)])
    billed = np.array([demand_hours[0] <= h < demand_hours[1] for h in range(24)])
    # Variables: 24 power values, tariff peak M and physical peak P.
    bounds = [(0, site_kw if available[h] else 0) for h in range(24)] + [(0, site_kw)] * 2
    rows = []
    for h in range(24):
        row = np.zeros(26)
        row[h], row[25] = 1, -1
        rows.append(row)
        if billed[h]:
            row = np.zeros(26)
            row[h], row[24] = 1, -1
            rows.append(row)
    eq = np.zeros((1, 26))
    eq[0, :24] = 1
    objective = np.zeros(26)
    objective[24] = 1
    first = linprog(objective, A_ub=np.array(rows), b_ub=np.zeros(len(rows)),
                    A_eq=eq, b_eq=[daily_grid_kwh], bounds=bounds, method="highs")
    total_hours = int(available.sum())
    if not first.success:
        if first.status != 2:
            raise RuntimeError(first.message)
        assert daily_grid_kwh > total_hours * site_kw - 1e-7
        return {"status": "INFEASIBLE_AGGREGATE_WINDOW",
                "unserved_grid_kwh_per_day_lower_bound": max(0, daily_grid_kwh - total_hours * site_kw)}
    off_hours = int((available & ~billed).sum())
    on_hours = total_hours - off_hours
    lower = max(0, (daily_grid_kwh - off_hours * site_kw) / on_hours) if on_hours else 0.0
    assert math.isclose(first.x[24], lower, abs_tol=1e-6)
    bounds[24] = (float(first.x[24]), float(first.x[24]))
    objective[24], objective[25] = 0, 1
    second = linprog(objective, A_ub=np.array(rows), b_ub=np.zeros(len(rows)),
                     A_eq=eq, b_eq=[daily_grid_kwh], bounds=bounds, method="highs")
    if not second.success:
        raise RuntimeError(second.message)
    power = second.x[:24]
    assert abs(power.sum() - daily_grid_kwh) < 1e-5
    assert max(power[~available], default=0) < 1e-7
    assert max(power) <= site_kw + 1e-7
    return {"status": "PASS_AGGREGATE_RELAXATION", "billed_peak_kw": float(first.x[24]),
            "physical_peak_kw": float(second.x[25]), "power_kw_by_clock_hour": power.tolist(),
            "analytic_billed_peak_lower_bound_kw": lower,
            "available_hours": total_hours, "nonbilled_available_hours": off_hours}


def annual_bill(daily_kwh: float, billed_peak_kw: float, energy_rate: float,
                demand_rate: float, basic_daily: float, rider: float,
                *, prior_11_demand_charges_cad: list[float] | None = None) -> dict:
    """Repeated steady daily use, April-2023 rates frozen for one 365-day year.

    For the steady benchmark, preceding monthly demand charges equal current
    demand charges. An explicit February--December prior-year charge history
    permits a low-use ratchet diagnostic and expires after eleven periods.
    Monthly periods are assumed wholly in calendar months in this comparison.
    No assertion about actual calendar-year 2023 invoice totals is made.
    """
    if min(daily_kwh, billed_peak_kw, energy_rate, demand_rate, basic_daily) < 0 or rider <= -1:
        raise ValueError("invalid billing input")
    prior = ([billed_peak_kw * demand_rate] * 11 if prior_11_demand_charges_cad is None
             else list(prior_11_demand_charges_cad))
    if len(prior) != 11 or min(prior) < 0:
        raise ValueError("eleven nonnegative preceding demand charges required")
    history = [(month, charge) for month, charge in zip(range(2, 13), prior)]
    months = []
    for month in range(1, 13):
        days = calendar.monthrange(2023, month)[1]
        energy, basic, demand = days * daily_kwh * energy_rate, days * basic_daily, billed_peak_kw * demand_rate
        minimum = 0.5 * max((charge for m, charge in history[-11:] if m in (11, 12, 1, 2, 3)), default=0)
        subtotal = energy + basic + demand
        months.append({"month": month, "energy_cad": energy, "basic_cad": basic,
                       "demand_cad": demand, "minimum_topup_cad": max(0, minimum - subtotal),
                       "minimum_cad_before_rider": minimum,
                       "bill_cad_after_rider_before_tax": max(subtotal, minimum) * (1 + rider)})
        history.append((month, demand))
    return {"annual_bill_cad_after_rider_before_tax": sum(m["bill_cad_after_rider_before_tax"] for m in months),
            "annual_energy_kwh": daily_kwh * 365,
            "annual_minimum_topup_cad": sum(m["minimum_topup_cad"] for m in months), "months": months}


def main() -> None:
    started = time.perf_counter()
    tariff = json.loads((ROOT / "data/processed/bchydro_2023_charging_tariffs.json").read_text())
    cases = []
    for intensity in (1.37, 1.6, 2.0):
        for efficiency in (0.85, 0.9, 0.95):
            for arrival in (20, 22, 0):
                a, depart = arrival, 6
                for site_kw in (2500, 3500, 5000):
                    daily = 100 * 68000 / 365 * intensity / efficiency
                    for name, rate in tariff["rates"].items():
                        solved = optimize_power(daily, a, depart, site_kw, tuple(rate["demand_clock_hours"]))
                        result = {"rate": name, "bus_equivalents": 100, "annual_km_per_equivalent": 68000,
                                  "battery_demand_kwh_per_km": intensity, "charging_efficiency": efficiency,
                                  "arrival_hour": a, "departure_hour": depart, "site_kw": site_kw,
                                  "daily_grid_kwh": daily, **solved}
                        if solved["status"].startswith("PASS"):
                            result.update(annual_bill(daily, solved["billed_peak_kw"], rate["energy_cad_per_kwh"],
                                                      rate["demand_cad_per_kw_month"], tariff["basic_cad_per_day"],
                                                      tariff["rate_rider_fraction"]))
                            result["fleet_rate_150kw_threshold_met"] = solved["physical_peak_kw"] >= 150
                        cases.append(result)
    central = [c for c in cases if c["battery_demand_kwh_per_km"] == 1.6
               and c["charging_efficiency"] == 0.9 and c["arrival_hour"] == 22
               and c["departure_hour"] == 6 and c["site_kw"] == 5000]
    overnight = next(c for c in central if c["rate"] == "1640")
    general = next(c for c in central if c["rate"] == "1600")
    daily_energy = overnight["daily_grid_kwh"]
    # For a 20:00--06:00 window: 8 unbilled hours and 2 billed hours.
    # With enough site power, RS1600 spreads over 10h; RS1640 first fills 8h.
    # Equality of the two annual bills gives this firm-power threshold.
    spread_general, spread_night = tariff["rates"]["1600"], tariff["rates"]["1640"]
    cross_kw = daily_energy * (0.4 + (spread_night["energy_cad_per_kwh"]
               - spread_general["energy_cad_per_kwh"]) * 365 / (12 * 12.5)) / 4
    crossing_bills = []
    for rate in (spread_general, spread_night):
        solved = optimize_power(daily_energy, 20, 6, cross_kw, tuple(rate["demand_clock_hours"]))
        crossing_bills.append(annual_bill(daily_energy, solved["billed_peak_kw"], rate["energy_cad_per_kwh"],
                              rate["demand_cad_per_kw_month"], tariff["basic_cad_per_day"],
                              tariff["rate_rider_fraction"])["annual_bill_cad_after_rider_before_tax"])
    assert abs(crossing_bills[0] - crossing_bills[1]) < 1e-5
    with (ROOT / "data/processed/translink_2023_energy_budget.csv").open(newline="") as stream:
        budget = {row["parameter"]: row for row in csv.DictReader(stream)}
    diesel_price = float(budget["diesel_price"]["value"])
    diesel = 100 * 68000 * 0.60 * diesel_price
    output = {"status": "CONDITIONAL_AGGREGATE_CHARGING_BOUND_NOT_CITY_SCORE",
              "source_file": "data/processed/bchydro_2023_charging_tariffs.json",
              "assumptions": {"bus_equivalents": "100 distance-equivalent normalizing units, not an observed fleet/one-for-one replacement count",
                              "annual_distance_source": "TransLink 2020 fleet plan, Appendix D: 68000 km per 40-ft vehicle per year",
                              "intensity_source": "Historical 40-ft 1.37--2.0 kWh/km range; 1.6 is in-route BEB reference, transferred to a hypothetical charging-window relaxation",
                              "consumption_boundary": "Battery-delivered energy is assumed here; dividing by charging efficiency is explicit and must be removed if a measured meter-energy intensity is used",
                              "diesel_budget_price": {"cad_per_litre": diesel_price, "source_file": "data/processed/translink_2023_energy_budget.csv", "status": "2023 budget assumption, not actual delivered price"},
                              "not_verified": ["actual nightly availability", "winter daily energy", "individual bus battery/payload feasibility", "charger port occupancy", "site connection capacity"],
                              "excludes": tariff["benchmark_exclusions"]},
              "central_cases": central,
              "central_comparison": {"overnight_vs_general_bill_reduction_pct": 100 * (1 - overnight["annual_bill_cad_after_rider_before_tax"] / general["annual_bill_cad_after_rider_before_tax"]),
                                     "minimum_site_kw_for_22_to_06_window": daily_energy / 8,
                                     "20_to_06_tariff_bill_crossover_site_kw": cross_kw,
                                     "20_to_06_incremental_kw_bill_saving_cad_per_year_before_capital": 12 * 12.5 * 4 * (1 + tariff["rate_rider_fraction"]),
                                     "20_to_06_crossover_independent_lp_bill_residual_cad": abs(crossing_bills[0] - crossing_bills[1]),
                                     "diesel_energy_only_cost_cad_at_2023_budget_price": diesel,
                                     "overnight_grid_energy_only_saving_vs_diesel_pct": 100 * (1 - overnight["annual_bill_cad_after_rider_before_tax"] / diesel),
                                     "warning": "Energy bills only. Not a complete project economic score, grant score, cost forecast or certified procurement alternative."},
              "all_cases": cases,
              "computation": {"device": "CPU", "scipy_version": scipy.__version__,
                              "case_count": len(cases), "additional_crossover_lp_checks": 2,
                              "elapsed_seconds": time.perf_counter() - started,
                              "checks": "Every feasible optimum matches independent closed-form cumulative-energy bound and has no power/window/energy residual violation"}}
    target = ROOT / "results/charging_tariff_bounds.json"
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"central_comparison": output["central_comparison"], "computation": output["computation"]}, indent=2))


if __name__ == "__main__":
    main()
