"""Create a transparent, like-for-like 2024--2033 transfer table.

The rows report planning positions, not certified delivered buses. Vancouver
uses active duty-block requests from the fall timetable and the 300-km
overnight-charge sensitivity. Chicago uses its public year-end inventory and
linearly replaces the non-electric stock. London uses its solved 17-year
chassis-life cohort schedule (not an asserted TfL life policy).
"""

import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    vancouver = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    london = json.loads((ROOT / "results/london_cohort_roadmap.json").read_text())
    life17 = next(x for x in london["scenarios"] if x["life_cap_years_scenario"] == 17)
    london_by_year = {x["year"]: x["total_slots_renewed"] for x in life17["annual_schedule"]}
    cta_total, cta_electric = 1875, 25
    cta_fossil = cta_total - cta_electric
    cta_annual = cta_fossil // 10
    cta_extra_first = cta_fossil - 10 * cta_annual
    records = []
    c_remaining = cta_fossil
    c_ev_stock = cta_electric
    london_ev_stock = 950
    for i, row in enumerate(vancouver["central_annual_inventory"], start=1):
        cta_count = cta_annual + (i <= cta_extra_first)
        c_remaining -= cta_count
        c_ev_stock += cta_count
        london_row = next(x for x in life17["annual_schedule"] if x["year"] == row["year"])
        london_ev_stock += london_row["non_electric_slots_converted"]
        records.append({"year": row["year"],
                        "vancouver_beb_purchases": row["total_beb_purchases"],
                        "vancouver_electric_vehicle_purchases": (
                            row["total_electric_vehicle_purchases"]
                        ),
                        "vancouver_electric_stock_end": row["electric_stock_end"],
                        "vancouver_conventional_stock_end": row["conventional_stock_end"],
                        "chicago_ev_replacements": cta_count,
                        "chicago_ev_stock_end": c_ev_stock,
                        "chicago_non_electric_remaining": max(0, c_remaining),
                        "london_17y_total_slots_renewed": london_by_year[row["year"]],
                        "london_ev_stock_end": london_ev_stock,
                        "london_non_electric_remaining": next(
                            x["remaining_non_electric_slots"] for x in life17["annual_schedule"]
                            if x["year"] == row["year"])})
    fieldnames = list(records[0])
    with (ROOT / "data/processed/three_city_roadmap_2023.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    rows = [r"\begin{table}[htbp]", r"\centering", r"\begin{tabular}{@{}rrrrrrrr@{}}", r"\toprule",
            r"Year & Van. EV buy & Van. EV & Van. fossil & CTA buy & CTA fossil & TfL buy & TfL fossil\\",
            r"\midrule"]
    for x in records:
        rows.append(f"{x['year']} & {x['vancouver_electric_vehicle_purchases']} & {x['vancouver_electric_stock_end']} & "
                    f"{x['vancouver_conventional_stock_end']} & {x['chicago_ev_replacements']} & "
                    f"{x['chicago_non_electric_remaining']} & {x['london_17y_total_slots_renewed']} & "
                    f"{x['london_non_electric_remaining']}" + "\\\\")
    rows += [r"\midrule",
             f"Total & {sum(x['vancouver_electric_vehicle_purchases'] for x in records)} & "
             f"{records[-1]['vancouver_electric_stock_end']} & {records[-1]['vancouver_conventional_stock_end']} & "
             f"{cta_fossil} & {records[-1]['chicago_non_electric_remaining']} & "
             f"{sum(london_by_year.values())} & {records[-1]['london_non_electric_remaining']}" + "\\\\",
             r"\bottomrule", r"\end{tabular}",
             r"\caption{Annual inventory path under three explicit planning models. Vancouver's 1,909 electric purchases comprise 1,647 route BEB positions plus 262 one-for-one trolley renewals; the stock endpoint remains 1,927 because replaced trolleys leave the fleet. Its 202 extra positions come from longer duty splits. Chicago purchases 1,850 electric replacements from a 1,875-bus inventory after 25 inferred electric buses. TfL renews 7,759 body-compatible positions under the 17-year scenario, including 7,693 non-electric conversions. Each model reaches zero non-electric stock in 2033; local garage and route feasibility is still required.}", r"\end{table}"]
    (ROOT / "paper/tables/three_city_roadmap.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    output = {"status": "TRANSFER_PLANNING_POSITIONS_NOT_DELIVERIES",
              "vancouver": {"basis": "class-specific aggregate core envelope; 300-km duty screen",
                            "initial_stock": vancouver["initial_stock_2023"],
                            "endpoint": vancouver["endpoint_2033"]},
              "chicago": {"basis": "2023 year-end inventory, 25 inferred June electric stock, linear replacement", "fleet": cta_total,
                          "initial_electric": cta_electric, "non_electric": cta_fossil, "annual": cta_annual},
              "london": {"basis": "31 March 2023 audit; 17-year chassis-life cohort scenario", "fleet": 8643,
                         "initial_electric": 950, "non_electric": 7693,
                         "total_renewals": sum(london_by_year.values()), "peak_annual_renewals": max(london_by_year.values())},
              "endpoint_2033": {
                  "vancouver_conventional": records[-1]["vancouver_conventional_stock_end"],
                  "chicago_conventional": records[-1]["chicago_non_electric_remaining"],
                  "london_conventional": records[-1]["london_non_electric_remaining"],
              },
              "annual_plan": records,
              "limits": ["Vancouver active block requests include extra sequential duties but not standby/spare buses.",
                         "Chicago electric stock is inferred from a June announcement and the linear conversion is a planning scenario, not an optimal driver schedule.",
                         "London renewals retain body-type availability by cohort; this is not a route forecast.",
                         "Local vehicle prices, tariffs and station constraints remain necessary before financial comparison across cities."]}
    (ROOT / "results/three_city_roadmap.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"],
                      "vancouver_endpoint": output["vancouver"]["endpoint"],
                      "chicago_endpoint": records[-1]["chicago_non_electric_remaining"],
                      "london_endpoint": records[-1]["london_non_electric_remaining"]}, indent=2))


if __name__ == "__main__":
    main()
