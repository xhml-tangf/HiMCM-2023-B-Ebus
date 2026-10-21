"""Verify that canonical manuscript fields resolve to generated values."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper/ebus_transition.tex"
MACROS = ROOT / "paper/generated/canonical_macros.tex"


def main() -> None:
    source = TEX.read_text(encoding="utf-8")
    if not MACROS.exists():
        raise SystemExit("canonical macros are missing; run scripts/build_paper_tables.py")
    macros = MACROS.read_text(encoding="utf-8")
    defined = set(re.findall(r"\\csname canonical@([^\\]+)\\endcsname\{", macros))
    used = set(re.findall(r"\\CV\{([^}]+)\}", source))
    missing = sorted(used - defined)
    if missing:
        raise SystemExit(f"unresolved canonical fields: {missing}")
    if "[canonical:" in source or "??" in source:
        raise SystemExit("placeholder canonical value remains in manuscript")
    if "UNVERIFIED" in source:
        raise SystemExit("main manuscript still contains repeated audit-status prose")
    required = {
        "schedule.fleet_with_spares", "schedule.required_peak_power_mw",
        "transition.plan_gross_pv_billion", "transition.baseline_gross_pv_billion",
        "lifecycle.environment_score_pct", "lifecycle.operation_reduction_pct",
    }
    if required - defined:
        raise SystemExit(f"headline fields absent from generated macros: {sorted(required-defined)}")
    for name in ("vancouver_scores.tex", "vancouver_roadmap.tex",
                 "three_city_comparison.tex", "canonical_sensitivity.tex",
                 "cost_lifecycle_tradeoff.png"):
        if not (ROOT / "paper/generated" / name).exists():
            raise SystemExit(f"generated paper asset missing: {name}")
    print(f"CANONICAL MANUSCRIPT CHECK PASS: {len(used)} used fields, {len(defined)} generated fields")


if __name__ == "__main__":
    main()
