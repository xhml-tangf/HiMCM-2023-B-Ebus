"""Execute the missing vehicle terminal-value comparison."""

from __future__ import annotations

import json
from pathlib import Path

from asset_boundary import (early_retirement_value, residual_fraction,
                            simulate_class, terminal_value, uniform_ages)

ROOT = Path(__file__).resolve().parents[1]


def discounted(value: float, year: int, rate: float = .03) -> float:
    return value / (1 + rate) ** (year - 2023)


def main() -> None:
    full = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    central = full["central_result"]
    inv = full["central_annual_inventory"]
    initial = full["initial_stock_2023"]
    initial_heavy = initial["heavy_conventional_scenario"]
    initial_deck = initial["double_deck_conventional_scenario"]
    initial_shuttle = initial["community_shuttle_conventional_scenario"]
    existing_beb = full["classes"]["existing_beb"]
    heavy_unit = central["heavy_unit_cost_cad"]
    deck_unit = central["deck_unit_cost_cad"]
    shuttle_unit = central["shuttle_unit_cost_cad"]
    baseline_heavy_unit = central["baseline_heavy_unit_cost_cad"]
    baseline_shuttle_unit = central["baseline_shuttle_unit_cost_cad"]
    existing_beb_unit = 1_200_000.0
    classes = {
        "heavy": dict(initial=initial_heavy, plan_unit=heavy_unit,
                      base_unit=baseline_heavy_unit),
        "shuttle": dict(initial=initial_shuttle, plan_unit=shuttle_unit,
                        base_unit=baseline_shuttle_unit),
    }
    # The public description gives a 32/25 split across 2019 and 2023 cohorts.
    deck_roles = {"double_deck": dict(initial=initial_deck,
                                      initial_ages={4: 32, 0: 25},
                                      plan_unit=deck_unit,
                                      base_unit=deck_unit)}
    base_terminal = {}; plan_terminal = {}; sale_events = {}
    base_costs = {}; plan_costs = {}
    for name, meta in {**classes, **deck_roles}.items():
        ages = meta.get("initial_ages") or uniform_ages(meta["initial"])
        prefix = {"heavy": "heavy", "shuttle": "shuttle",
                  "double_deck": "double_deck"}[name]
        if name == "heavy":
            b_pur = {row["year"]: row["baseline_heavy_purchases"] for row in inv}
            b_ret = {}
            p_pur = {row["year"]: row["heavy_beb_purchases"] for row in inv}
            p_ret = {row["year"]: row["heavy_conventional_retirements"] for row in inv}
        elif name == "shuttle":
            b_pur = {row["year"]: row["baseline_shuttle_purchases"] for row in inv}
            b_ret = {}
            p_pur = {row["year"]: row["shuttle_beb_purchases"] for row in inv}
            p_ret = {row["year"]: row["shuttle_retirements"] for row in inv}
        else:
            b_pur = {row["year"]: row["baseline_double_deck_purchases"] for row in inv}
            b_ret = {}
            p_pur = {row["year"]: row["double_deck_beb_purchases"] for row in inv}
            p_ret = {row["year"]: row["double_deck_retirements"] for row in inv}
        # Missing baseline retirement rows imply no scheduled replacement. For
        # heavy and shuttle, use the observed number of new conventional buses
        # as the retirement count because the ordinary-renewal model buys one
        # equivalent vehicle for each position it replaces.
        if not b_ret:
            b_ret = {year: b_pur.get(year, 0) for year in range(2024, 2034)}
        base_ages, _ = simulate_class(ages, b_pur, b_ret)
        plan_ages, plan_retired = simulate_class(ages, p_pur, p_ret)
        base_terminal[name] = terminal_value(base_ages, meta["base_unit"])
        plan_terminal[name] = terminal_value(plan_ages, meta["plan_unit"])
        base_costs[name] = p_pur
        for year, retired in plan_retired.items():
            sale_events[(name, year)] = (retired, meta["plan_unit"])
    # Existing electric buses survive in both paths and were omitted from the
    # purchase-only residual function.
    existing_ages = {10: existing_beb}
    existing_pv = discounted(terminal_value(existing_ages, existing_beb_unit), 2033)
    base_terminal_total = sum(base_terminal.values())
    plan_terminal_total = sum(plan_terminal.values())
    base_terminal_pv = discounted(base_terminal_total, 2033)
    plan_terminal_pv = discounted(plan_terminal_total, 2033)
    sale_cases = []
    for recovery in (0.0, 0.10, 0.25):
        nominal = sum(
            discounted(early_retirement_value(retired, unit, recovery), year)
            for (_, year), (retired, unit) in sale_events.items())
        adjusted_plan = central["plan_gross_pv_cad"] - existing_pv - nominal
        adjusted_base = central["baseline_gross_pv_cad"] - base_terminal_pv - existing_pv
        sale_cases.append({
            "market_recovery_fraction_for_remaining_book_proxy": recovery,
            "period_disposal_receipts_pv_cad": nominal,
            "asset_adjusted_baseline_pv_cad": adjusted_base,
            "asset_adjusted_plan_pv_cad": adjusted_plan,
            "asset_adjusted_economic_score_pct": 100 * (adjusted_base - adjusted_plan) / adjusted_base,
        })
    # Infrastructure is a separate sensitivity because service life and
    # terminal ownership are not published.
    infra = {"shared": central["shared_depot_cad"],
             "class": central["additional_class_capital_cad"]}
    infra_cases = []
    for life in (20, 30, 40):
        nominal = sum(total / 8 * residual_fraction(2033 - year, life)
                      for total in infra.values() for year in range(2024, 2032))
        infra_cases.append({"straight_line_life_years": life,
                            "terminal_value_2033_nominal_cad": nominal,
                            "terminal_value_pv_cad": discounted(nominal, 2033)})
    combined_cases = []
    for sale in sale_cases:
        for infra_case in [{"straight_line_life_years": None,
                            "terminal_value_pv_cad": 0.0}] + infra_cases:
            plan_value = (sale["asset_adjusted_plan_pv_cad"]
                          - infra_case["terminal_value_pv_cad"])
            base_value = sale["asset_adjusted_baseline_pv_cad"]
            combined_cases.append({
                "market_recovery_fraction": sale["market_recovery_fraction_for_remaining_book_proxy"],
                "infrastructure_life_years": infra_case["straight_line_life_years"],
                "planned_infrastructure_terminal_pv_cad": infra_case["terminal_value_pv_cad"],
                "baseline_asset_adjusted_pv_cad": base_value,
                "plan_asset_infrastructure_adjusted_pv_cad": plan_value,
                "economic_score_pct": 100 * (base_value - plan_value) / base_value,
            })
    output = {
        "status": "UNIFORM_INITIAL_AGE_AND_MARKET_RECOVERY_SCENARIOS_NOT_BOOK_VALUE",
        "initial_age_scenario": "Uniform ages 0--16 for heavy non-deck and community shuttles; 32 double-decks age 4 and 25 age 0 at end-2023; existing 18 BEBs age 10 at horizon.",
        "life_years": 17,
        "initial_terminal_value": {
            "baseline_by_class_nominal_cad": base_terminal,
            "plan_by_class_nominal_cad": plan_terminal,
            "baseline_pv_cad": base_terminal_pv,
            "plan_pv_cad": plan_terminal_pv,
            "existing_beb_common_pv_cad": existing_pv,
        },
        "asset_adjusted_cases": sale_cases,
        "infrastructure_terminal_sensitivity": infra_cases,
        "combined_asset_and_infrastructure_cases": combined_cases,
        "battery_replacement_boundary": {
            "new_beb_battery_replacement_within_2024_2033": 0,
            "reason": "The readiness-aligned 2029--2033 purchase schedule does not reach an assumed eight-year battery interval before 2033.",
            "future_obligation": "Batteries commissioned in 2029--2033 fall due after the decision horizon and must be carried as a future replacement reserve.",
        },
        "excluded": [
            "site-specific disposal costs",
            "actual used-bus market bids",
            "incremental driver and deadhead cash flows",
            "future out-of-horizon battery replacements",
            "infrastructure ownership or removal liabilities",
        ],
        "boundaries": [
            "Replacement-cost proxies are applied to unknown-age initial assets; they are not accounting book values.",
            "Both paths use the same initial age scenario and straight-line life. The baseline keeps the younger double-deck cohort at the 2033 endpoint.",
            "Market recovery percentages are disclosed policy cases, not observed bids.",
        ],
    }
    (ROOT / "results/vancouver_asset_boundary.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"initial_terminal_value": output["initial_terminal_value"],
                      "asset_adjusted_cases": sale_cases,
                      "infrastructure_terminal_sensitivity": infra_cases}, indent=2))


if __name__ == "__main__":
    main()
