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
    assert omitted["future_battery_capacity_kwh"] == 543_615
