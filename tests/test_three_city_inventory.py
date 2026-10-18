import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_three_city_inventory_endpoints_are_explicit():
    result = json.loads((ROOT / "results/three_city_roadmap.json").read_text())
    rows = pd.read_csv(ROOT / "data/processed/three_city_roadmap_2023.csv")
    assert len(rows) == 10
    assert rows.vancouver_beb_purchases.sum() == 1647
    assert rows.vancouver_electric_vehicle_purchases.sum() == 1909
    assert rows.vancouver_conventional_stock_end.iloc[-1] == 0
    assert rows.vancouver_electric_stock_end.iloc[-1] == 1927
    assert rows.chicago_non_electric_remaining.iloc[-1] == 0
    assert rows.london_non_electric_remaining.iloc[-1] == 0
    assert result["vancouver"]["endpoint"]["conventional_stock"] == 0
    assert result["endpoint_2033"] == {
        "vancouver_conventional": 0,
        "chicago_conventional": 0,
        "london_conventional": 0,
    }
