from math import isclose
import json
from pathlib import Path

from src.asset_boundary import (early_retirement_value, residual_fraction,
                                retire_oldest, simulate_class, terminal_value,
                                uniform_ages)


def test_age_ledger_conserves_counts_and_retires_oldest():
    ages = uniform_ages(17)
    remaining, retired = retire_oldest(ages, 2)
    assert sum(remaining.values()) + sum(retired.values()) == 17
    assert retired == {16: 1, 15: 1}
    assert sum(remaining.values()) == 15


def test_terminal_value_includes_pre_horizon_stock():
    assert residual_fraction(10) == 7 / 17
    assert isclose(terminal_value({10: 25}, 1.0), 25 * 7 / 17)
    assert isclose(early_retirement_value({4: 32}, 1.0, .10), 32 * .10 * 13 / 17)


def test_purchase_and_retirement_ledger_balances():
    ages, retired = simulate_class(
        {0: 2}, {}, {2024: 1, 2025: 1})
    assert sum(ages.values()) == 0
    assert sum(sum(x.values()) for x in retired.values()) == 2


def test_asset_json_reports_omitted_operating_and_battery_sensitivities():
    result = json.loads((Path(__file__).resolve().parents[1]
                         / "results/vancouver_asset_boundary.json").read_text())
    omitted = result["operating_omission_sensitivity"]
    assert omitted["extra_service_positions"] == 202
    assert omitted["driver_pv_range_cad"][0] < omitted["driver_pv_range_cad"][1]
    assert omitted["future_battery_capacity_kwh"] == 539_260


def test_unified_terminal_ledger_credits_each_asset_once():
    root = Path(__file__).resolve().parents[1]
    result = json.loads((root / "results/vancouver_asset_boundary.json").read_text())
    full = json.loads((root / "results/vancouver_full_fleet_bound.json").read_text())
    central = full["central_result"]
    ledger = result["terminal_reconciliation"]
    initial = result["initial_terminal_value"]
    # Independent individual-vehicle reconstruction, tagging initial vs new.
    # Do not reuse simulate_class or terminal_value from the implementation.
    expected = 0.0
    for stock, price, purchases in (("heavy_conventional_scenario", "baseline_heavy_unit_cost_cad", "baseline_heavy_purchases"),
                         ("community_shuttle_conventional_scenario", "baseline_shuttle_unit_cost_cad", "baseline_shuttle_purchases")):
        q, rem = divmod(full["initial_stock_2023"][stock], 17)
        fleet = [(2023-a, True) for a in range(17) for _ in range(q+(a < rem))]
        for row in full["central_annual_inventory"]:
            count = row[purchases]
            fleet = sorted(fleet)[count:] + [(row["year"], False)] * count
        expected += sum(max(0, 17-(2033-born))/17 * central[price]
                        for born, is_initial in fleet if is_initial)
    expected += (32*3 + 25*7) / 17 * central["deck_unit_cost_cad"]
    assert isclose(initial["baseline_pv_cad"], expected / 1.03**10, abs_tol=1e-6)
    for side in ("baseline", "plan"):
        assert isclose(ledger[f"{side}_all_pv_cad"],
                       ledger[f"{side}_new_already_credited_pv_cad"] + initial[f"{side}_pv_cad"], abs_tol=1e-6)
    zero_sale = result["asset_adjusted_cases"][0]
    assert isclose(zero_sale["asset_adjusted_baseline_pv_cad"],
                   central["baseline_gross_pv_cad"] - expected / 1.03**10
                   - initial["existing_beb_common_pv_cad"], abs_tol=1e-6)
    assert isclose(initial["plan_pv_cad"], 0, abs_tol=1e-6)
    assert isclose(zero_sale["asset_adjusted_plan_pv_cad"],
                   central["plan_gross_pv_cad"] - initial["existing_beb_common_pv_cad"], abs_tol=1e-6)
