"""Create a transparent, like-for-like 2024--2033 transfer table.

The rows report planning positions, not certified delivered buses. Vancouver
uses active duty-block requests from the fall timetable and the 300-km
overnight-charge sensitivity. Chicago uses its public year-end inventory and
linearly replaces the non-electric stock. London uses its solved 17-year
chassis-life cohort schedule (not an asserted TfL life policy).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    vancouver = json.loads((ROOT / "results/vancouver_transition_scenarios.json").read_text())
    london = json.loads((ROOT / "results/london_cohort_roadmap.json").read_text())
    life17 = next(x for x in london["scenarios"] if x["life_cap_years_scenario"] == 17)
    london_by_year = {x["year"]: x["total_slots_renewed"] for x in life17["annual_schedule"]}
    cta_total, cta_electric = 1875, 25
    cta_fossil = cta_total - cta_electric
    cta_annual = cta_fossil // 10
    cta_extra_first = cta_fossil - 10 * cta_annual
    records = []
    v_remaining = vancouver["service_baseline"]["active_non_trolley_blocks"]
    c_remaining = cta_fossil
    for i, row in enumerate(vancouver["roadmap"], start=1):
        cta_count = cta_annual + (i <= cta_extra_first)
        c_remaining -= cta_count
        v_remaining -= row["plan_bus_purchases"]
        records.append({"year": row["year"], "vancouver_ev_active_block_requests": row["plan_bus_purchases"],
                        "vancouver_renewal_baseline": row["baseline_bus_purchases"],
                        "chicago_ev_replacements": cta_count, "london_17y_total_slots_renewed": london_by_year[row["year"]],
                        "vancouver_active_blocks_remaining": max(0, v_remaining),
                        "chicago_non_electric_remaining": max(0, c_remaining),
                        "london_non_electric_remaining": next(
                            x["remaining_non_electric_slots"] for x in life17["annual_schedule"]
                            if x["year"] == row["year"])})
    (ROOT / "data/processed/three_city_roadmap_2023.csv").write_text(
        "year,vancouver_ev_active_block_requests,vancouver_renewal_baseline,chicago_ev_replacements,"
        "london_17y_total_slots_renewed,vancouver_active_blocks_remaining,chicago_non_electric_remaining,"
        "london_non_electric_remaining\n" + "\n".join(
            ",".join(str(row[k]) for k in ("year", "vancouver_ev_active_block_requests", "vancouver_renewal_baseline",
                                           "chicago_ev_replacements", "london_17y_total_slots_renewed",
                                           "vancouver_active_blocks_remaining", "chicago_non_electric_remaining",
                                           "london_non_electric_remaining")) for row in records) + "\n",
        encoding="utf-8")
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}rrrrr@{}}", r"\toprule",
            r"Year & Vancouver EV & Renewal base & Chicago EV & London renewals\\",
            r"\midrule"]
    for x in records:
        rows.append(f"{x['year']} & {x['vancouver_ev_active_block_requests']} & {x['vancouver_renewal_baseline']} & "
                    f"{x['chicago_ev_replacements']} & {x['london_17y_total_slots_renewed']}" + "\\\\")
    rows += [r"\midrule",
             f"Total & {sum(x['vancouver_ev_active_block_requests'] for x in records)} & "
             f"{sum(x['vancouver_renewal_baseline'] for x in records)} & {cta_fossil} & "
             f"{sum(london_by_year.values())}" + "\\\\",
             r"\bottomrule", r"\end{tabular}",
             r"\caption{Transferable ten-year purchase plans. Vancouver reports net new battery-bus planning positions after the 18 existing BEBs, derived from a 1,463-bus non-trolley fleet and the 300-km block-request ratio; 57 double-deck vehicles and 262 trolleys are separate. Chicago linearly replaces the non-electric year-end inventory; London renews registration chunks under a 17-year chassis-life scenario, including existing EVs. These are planning positions, not verified orders or route-feasible purchases.}", r"\end{table}"]
    (ROOT / "paper/tables/three_city_roadmap.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    output = {"status": "TRANSFER_PLANNING_POSITIONS_NOT_DELIVERIES",
              "vancouver": {"basis": "active non-trolley duty blocks; 300-km overnight-charge screening", **vancouver["service_baseline"]},
              "chicago": {"basis": "2023 year-end inventory, 25 inferred June electric stock, linear replacement", "fleet": cta_total,
                          "initial_electric": cta_electric, "non_electric": cta_fossil, "annual": cta_annual},
              "london": {"basis": "31 March 2023 audit; 17-year chassis-life cohort scenario", "fleet": 8643,
                         "initial_electric": 950, "non_electric": 7693,
                         "total_renewals": sum(london_by_year.values()), "peak_annual_renewals": max(london_by_year.values())},
              "annual_plan": records,
              "limits": ["Vancouver active block requests include extra sequential duties but not standby/spare buses.",
                         "Chicago electric stock is inferred from a June announcement and the linear conversion is a planning scenario, not an optimal driver schedule.",
                         "London renewals retain body-type availability by cohort; this is not a route forecast.",
                         "Local vehicle prices, tariffs and station constraints remain necessary before financial comparison across cities."]}
    (ROOT / "results/three_city_roadmap.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
