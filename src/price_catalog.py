"""Source-labelled leaves shared by all Vancouver financial scenarios."""
from pathlib import Path
import json
try:
    from .price_index import price_record
except ImportError:
    from price_index import price_record


def catalog():
    # CAD amounts from the listed source scope; project envelopes are not bids.
    entries = {
        "baseline_cng": (46143000/50, 2024, "budget2024", "50 CNG project: CAD 46.143m/50"),
        "hardware": (1200000, 2023, "june2023tech", "Generic BEB hardware screen"),
        "project_standard": (106846000/57, 2025, "budget2025", "57 BEB project: CAD 106.846m/57"),
        "project_articulated": (3037000, 2025, "budget2025", "Articulated BEB project envelope per bus, source rounded"),
        "depot_per_bus": (500000000/340, 2023, "june2023tech", "Marpole CAD 500m/340 slots"),
        "onroute": (610000, 2023, "june2023tech", "In-route equipment screen"),
        "infrastructure_high": (6520000000, 2024, "playbook2024", "Multi-site/expansion envelope; alternative, not additive"),
        "baseline_shuttle": (16265000/54, 2025, "budget2025", "54 conventional shuttle project: CAD 16.265m/54"),
        "trolley_standard": (414600000/188, 2025, "budget2025", "188 common standard trolley replacements"),
        "trolley_articulated": (182900000/73, 2025, "budget2025", "73 common articulated trolley replacements"),
        "trolley_pilot": (3550000, 2025, "budget2025", "Common trolley pilot replacement"),
        "om_diesel": (3.30, 2024, "playbook2024", "Diesel O&M CAD/service-km"),
        "om_hybrid": (1.97, 2024, "playbook2024", "Hybrid O&M CAD/service-km"),
        "om_cng": (2.77, 2024, "playbook2024", "CNG O&M CAD/service-km"),
        "om_beb": (2.28, 2024, "playbook2024", "BEB O&M CAD/service-km"),
    }
    return {key: price_record(amount, year, source_id=source, source_scope=scope)
            for key, (amount, year, source, scope) in entries.items()}


def price(key):
    return catalog()[key]["value_2023_cad"]


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    (root / "results/vancouver_price_ledger.json").write_text(
        json.dumps(catalog(), indent=2) + "\n", encoding="utf-8")
