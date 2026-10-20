from math import isclose

from src.price_index import factors, to_2023
from src.audit_deck_shuttle_electrification import scenario_prices, SCENARIOS


def test_cpi_rebases_price_years_to_2023():
    f = factors()
    assert set(f) == set(range(2019, 2026))
    assert f[2023] == 1.0
    assert isclose(to_2023(100, 2024), 100 * f[2024])
    assert 0.95 < f[2025] < 1.0


def test_price_sources_and_mixed_year_infrastructure_are_rebased_separately():
    low = scenario_prices("double_deck", "low", SCENARIOS["low"]["double_deck"])
    assert isclose(low["vehicle"]["value_2023_cad"], 1165000 * 1.35 * factors()[2021])
    central = scenario_prices("double_deck", "central", SCENARIOS["central"]["double_deck"])
    assert central["charger"]["source_year"] == 2019
    assert central["depot"]["source_year"] == 2023
    assert isclose(central["charger"]["value_2023_cad"], 1300000 * factors()[2019])
    shuttle = scenario_prices("community_shuttle", "central", SCENARIOS["central"]["community_shuttle"])
    assert isclose(shuttle["vehicle"]["value_2023_cad"], 6000000 / 14 * factors()[2021])


def test_class_builder_uses_already_rebased_leaves_without_second_cpi():
    from math import ceil
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "results/vancouver_full_fleet_bound.json").read_text())
    for case in data["economics"]:
        name = case["case"]
        d = scenario_prices("double_deck", name, SCENARIOS[name]["double_deck"])
        s = scenario_prices("community_shuttle", name, SCENARIOS[name]["community_shuttle"])
        assert isclose(case["deck_unit_cost_cad"], d["vehicle"]["value_2023_cad"])
        assert isclose(case["shuttle_unit_cost_cad"], s["vehicle"]["value_2023_cad"])
        assert isclose(case["additional_class_capital_cad"],
                       57*d["depot"]["value_2023_cad"] + 9*d["charger"]["value_2023_cad"]
                       + ceil(SCENARIOS[name]["community_shuttle"]["fleet_low"] /
                              SCENARIOS[name]["community_shuttle"]["vehicles_per_charger"])
                       * s["charger"]["value_2023_cad"])
