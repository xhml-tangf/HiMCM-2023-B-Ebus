"""Guard key manuscript results against stale generated JSON values."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    text = (ROOT / "paper/ebus_transition.tex").read_text(encoding="utf-8")
    generic = json.loads((ROOT / "results/vancouver_transition_scenarios.json").read_text())
    central_generic = next(x for x in generic["economics"] if x["case"] == "central")
    env_min = min(x["environment_score_boundary_pct"] for x in generic["environment"])
    env_max = max(x["environment_score_boundary_pct"] for x in generic["environment"])
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    central_full = full["central_result"]
    env_full_min = min(x["environment_score_pct"] for x in full["environment_central"])
    env_full_max = max(x["environment_score_pct"] for x in full["environment_central"])
    expected = [
        f"{central_generic['plan_gross_pv_cad'] / 1e9:.2f}",
        f"{central_generic['baseline_gross_pv_cad'] / 1e9:.2f}",
        f"{central_generic['economic_score_gross_pct']:.1f}",
        f"{env_min:.1f}--{env_max:.1f}",
        "1,419",
        "1,401",
        "1,647",
        "1,909",
        "1,927",
        f"{central_full['plan_gross_pv_cad'] / 1e9:.2f}",
        f"{central_full['baseline_gross_pv_cad'] / 1e9:.2f}",
        f"{central_full['economic_score_gross_pct']:.1f}",
        f"{env_full_min:.1f}--{env_full_max:.1f}",
    ]
    missing = [value for value in expected if value not in text]
    stale = [
        value for value in (
            "4.709", "5.259", "-91.6", "35.1--84.0",
            "1,652", "1,932", "-81.7", "-104.1",
        ) if value in text
    ]
    if missing or stale:
        raise SystemExit(f"Manuscript number check failed: missing={missing}, stale={stale}")
    print("MANUSCRIPT NUMBER CHECK PASS: generic, class-specific and endpoint values agree")


if __name__ == "__main__":
    main()
