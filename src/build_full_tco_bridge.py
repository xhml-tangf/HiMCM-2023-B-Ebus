"""Close omitted annualized operating components around the class cost case.

TransLink's 2020 appendix D gives 2019-CAD lifecycle rates for charger
maintenance, mid-life battery replacement and extra operator labour. These are
annualized, 17-year per-service-km rates. Apply only the components absent from
the central O&M ledger, separately, to avoid duplicating bus maintenance, fuel,
or infrastructure capital. They are a sensitivity bridge because the source is
2019 technology and not a 2024--2033 local invoice.
"""
from __future__ import annotations

import json
from pathlib import Path

from price_index import price_record

ROOT = Path(__file__).resolve().parents[1]
RATE = 0.03


def pv(cash: dict[int, float]) -> float:
    return sum(value / (1+RATE)**(year-2023) for year, value in cash.items())


def main() -> None:
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    central = full["central_result"]
    ledger = full["annual_service_ledger"]
    leaves = {
        "battery_replacement": price_record(0.07, 2019, source_id="fleet2020",
            source_scope="Appendix D, lower 2019-CAD mid-life battery replacement rate per service-km"),
        "battery_replacement_high": price_record(0.20, 2019, source_id="fleet2020",
            source_scope="Appendix D, upper 2019-CAD mid-life battery replacement rate per service-km"),
        "charger_maintenance": price_record(0.03, 2019, source_id="fleet2020",
            source_scope="Appendix D, lower 2019-CAD charger maintenance rate per service-km"),
        "charger_maintenance_high": price_record(0.05, 2019, source_id="fleet2020",
            source_scope="Appendix D, upper 2019-CAD charger maintenance rate per service-km"),
        "extra_operator": price_record(0.02, 2019, source_id="fleet2020",
            source_scope="Appendix D, lower electric-bus operator labour increment per service-km"),
        "extra_operator_high": price_record(0.16, 2019, source_id="fleet2020",
            source_scope="Appendix D, upper electric-bus operator labour increment per service-km"),
    }
    low_rate = sum(leaves[k]["value_2023_cad"] for k in
                   ("battery_replacement", "charger_maintenance", "extra_operator"))
    high_rate = sum(leaves[k]["value_2023_cad"] for k in
                    ("battery_replacement_high", "charger_maintenance_high", "extra_operator_high"))
    annual_low = {x["year"]: x["electric_km"]*low_rate for x in ledger}
    annual_high = {x["year"]: x["electric_km"]*high_rate for x in ledger}
    add_low, add_high = pv(annual_low), pv(annual_high)
    baseline = central["baseline_gross_pv_cad"]
    plan = central["plan_gross_pv_cad"]
    cases = []
    for name, add in (("low", add_low), ("high", add_high)):
        adjusted = plan + add
        cases.append({"case": name, "annualized_rate_2023_cad_per_electric_km":
                      low_rate if name == "low" else high_rate,
                      "added_pv_cad": add, "plan_full_tco_pv_cad": adjusted,
                      "economic_score_pct": 100*(baseline-adjusted)/baseline})
    asset = json.loads((ROOT / "results/vancouver_asset_boundary.json").read_text())
    output = {
        "status": "SOURCE_LABELLED_ANNUALIZED_TCO_BRIDGE_NOT_LOCAL_QUOTE_OR_FORECAST",
        "base_year": 2023, "discount_rate_real": RATE,
        "price_leaves": leaves, "cases": cases,
        "included_to_avoid_double_counting": [
            "charger maintenance", "mid-life battery replacement reserve",
            "extra operator labour for electric layover/deadhead"],
        "already_in_central_ledger_not_added": [
            "vehicle and infrastructure capital", "bus maintenance and energy",
            "demand and commodity electricity charges", "vehicle residual"],
        "separate_overlapping_scenarios_not_added": json.loads(
            json.dumps(asset["operating_omission_sensitivity"])),
        "scope": "Electric service kilometres in the class-specific 2024--2033 ledger only.",
        "boundary": "The rates come from a 2019 40-ft lifecycle case, not local 2024--2033 invoices. They are annualized reserves and are not the year in which a battery or charger is procured. Training, insurance, tax, financing, local site upgrades and post-horizon replacement of newly installed assets remain outside the two scores.",
    }
    (ROOT / "results/vancouver_full_tco_bridge.json").write_text(
        json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
