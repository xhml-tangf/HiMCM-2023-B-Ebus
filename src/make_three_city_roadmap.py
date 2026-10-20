"""Create a transparent, like-for-like 2024--2033 transfer table.

The rows report planning positions, not certified delivered buses. Vancouver
uses active duty-block requests from the fall timetable and the 300-km
overnight-charge sensitivity. Chicago keeps its legacy linear inventory column
for continuity and adds a separate hard-age cohort test against the 185-bus
annual purchase capacity. London uses its solved 17-year chassis-life cohort
schedule (not an asserted TfL life policy).
"""

import json
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EOL = "\\\\"
YEARS = list(range(2024, 2034))
CTA_FLEET = 1875
CTA_INITIAL_ELECTRIC = 25
CTA_ANNUAL_CAPACITY = 185
CTA_LIFE_CAPS = (17, 14, 12)


def load_cta_age_cohorts() -> list[dict]:
    """Load the reported CTA age bins without inventing individual ages."""
    with (ROOT / "data/processed/cta_2023_age_cohorts.csv").open(
            newline="", encoding="utf-8") as handle:
        rows = []
        for raw in csv.DictReader(handle):
            row = {"vehicle_type": raw["vehicle_type"],
                   "age_low": int(raw["age_low"]),
                   "age_high": int(raw["age_high"]),
                   "vehicles": int(raw["vehicles"])}
            assert row["age_low"] <= row["age_high"]
            assert row["vehicles"] > 0
            rows.append(row)
    assert sum(row["vehicles"] for row in rows) == CTA_FLEET
    assert sum(row["vehicles"] for row in rows if row["vehicle_type"] == "Bus") == 1576
    assert sum(row["vehicles"] for row in rows
               if row["vehicle_type"] == "Articulated Bus") == 299
    return rows


def build_cta_age_scenario(cohorts: list[dict], life_cap: int,
                           annual_capacity: int = CTA_ANNUAL_CAPACITY) -> dict:
    """Stress the inventory against every cohort's oldest possible age.

    A reported bin ``[a_low, a_high]`` does not identify individual build
    years.  The robust deadline therefore uses ``a_high``: every member is
    assumed to have reached the oldest age compatible with the published bin.
    This is the only deadline that keeps *all* vehicles below the cap without
    setting individual ages.  The resulting 2024 counts match the published
    CTA audit's definitely-due bins.
    """
    if life_cap not in CTA_LIFE_CAPS:
        raise ValueError(f"Unsupported CTA life cap: {life_cap}")
    if annual_capacity <= 0:
        raise ValueError("Annual purchase capacity must be positive")

    due_by_year = {year: {"Bus": 0, "Articulated Bus": 0} for year in YEARS}
    deadline_cohorts = []
    for cohort in cohorts:
        deadline = max(2024, 2023 + life_cap - cohort["age_high"])
        if deadline > 2033:
            continue
        due_by_year[deadline][cohort["vehicle_type"]] += cohort["vehicles"]
        deadline_cohorts.append({
            **cohort,
            "deadline_year": deadline,
            "deadline_rule": "2023 + life_cap - age_high, floored at 2024",
        })
    deadline_cohorts.sort(key=lambda row: (row["deadline_year"], row["vehicle_type"],
                                           row["age_low"]))

    non_electric = CTA_FLEET - CTA_INITIAL_ELECTRIC
    annual = []
    cumulative_due = 0
    peak_shortfall = 0
    peak_shortfall_year = None
    first_shortfall_year = None
    for year_index, year in enumerate(YEARS, start=1):
        standard_due = due_by_year[year]["Bus"]
        articulated_due = due_by_year[year]["Articulated Bus"]
        due = standard_due + articulated_due
        cumulative_due += due
        cumulative_capacity = annual_capacity * year_index
        overdue = max(0, cumulative_due - cumulative_capacity)
        on_time_replacements = min(due, annual_capacity)
        peak_shortfall = max(peak_shortfall, overdue)
        if overdue and peak_shortfall == overdue:
            peak_shortfall_year = year
        if overdue and first_shortfall_year is None:
            first_shortfall_year = year
        annual.append({
            "year": year,
            "standard_bus_age_due": standard_due,
            "articulated_bus_age_due": articulated_due,
            "age_due_slots": due,
            "cumulative_age_due_slots": cumulative_due,
            "annual_purchase_capacity": annual_capacity,
            "cumulative_purchase_capacity": cumulative_capacity,
            "on_time_replacements_assigned_to_new_deadline": on_time_replacements,
            "newly_due_slots_missed_in_year": due - on_time_replacements,
            "overdue_age_slots_after_year": overdue,
        })

    age_due_2033 = sum(row["age_due_slots"] for row in annual)
    age_due_2033_standard = sum(row["standard_bus_age_due"] for row in annual)
    age_due_2033_articulated = sum(row["articulated_bus_age_due"] for row in annual)
    age_only_peak = max(math.ceil(row["cumulative_age_due_slots"] /
                                  (row["year"] - 2023))
                        for row in annual)
    electrification_peak = math.ceil(non_electric / len(YEARS))
    required_peak = max(age_only_peak, electrification_peak)
    latest_capacity_shortfall = annual[-1]["overdue_age_slots_after_year"]
    maximum_on_time_replacements = sum(
        min(row["age_due_slots"], annual_capacity) for row in annual)
    minimum_late_slots = age_due_2033 - maximum_on_time_replacements
    assert minimum_late_slots == peak_shortfall
    return {
        "life_cap_years_scenario": life_cap,
        "fleet_slots": CTA_FLEET,
        "initial_electric_slots_inferred": CTA_INITIAL_ELECTRIC,
        "initial_non_electric_slots": non_electric,
        "annual_purchase_capacity": annual_capacity,
        "capacity_basis": (
            "SCREENING ASSUMPTION: the legacy 1,850/10 linear pace is used as a "
            "185-bus annual cap; it is not an observed CTA procurement ceiling."
        ),
        "on_time_priority_rule": (
            "At most 185 purchases are assigned to newly due vehicles in a year; "
            "spare capacity is assigned to prior backlog. A missed deadline remains "
            "a breach even if the vehicle is replaced later."
        ),
        "robust_age_assumption": (
            "Each reported age bin is retired by the year its oldest member reaches "
            "the cap; individual vehicle ages are not available."
        ),
        "due_2024_slots": annual[0]["age_due_slots"],
        "due_2024_standard_buses": annual[0]["standard_bus_age_due"],
        "due_2024_articulated_buses": annual[0]["articulated_bus_age_due"],
        "shortfall_2024_slots": annual[0]["overdue_age_slots_after_year"],
        "age_due_by_2033_slots": age_due_2033,
        "age_due_by_2033_standard_buses": age_due_2033_standard,
        "age_due_by_2033_articulated_buses": age_due_2033_articulated,
        "minimum_age_only_peak_annual_renewals": age_only_peak,
        "minimum_uniform_annual_capacity_with_2033_electrification": required_peak,
        "minimum_total_purchases_through_2033_age_and_target_lower_bound": max(
            age_due_2033, non_electric),
        "hard_age_compliant_at_annual_capacity": first_shortfall_year is None,
        "first_deadline_shortfall_year": first_shortfall_year,
        "peak_cumulative_shortfall_slots": peak_shortfall,
        "peak_cumulative_shortfall_year": peak_shortfall_year,
        "closing_age_shortfall_slots": latest_capacity_shortfall,
        "minimum_slots_missing_hard_deadline": minimum_late_slots,
        "deadline_breaches_are_irrecoverable": minimum_late_slots > 0,
        "purchase_type_mix_certified": False,
        "initial_electric_age_allocation": (
            "UNVERIFIED: the age table covers all 1,875 buses and does not identify "
            "which slots are the 25 inferred electric buses."
        ),
        "additional_age_renewals_uncertainty_from_initial_electric_slots": [
            0, CTA_INITIAL_ELECTRIC],
        "annual_schedule": annual,
        "deadline_cohorts": deadline_cohorts,
    }


def build_cta_age_model(cohorts: list[dict]) -> dict:
    scenarios = [build_cta_age_scenario(cohorts, life) for life in CTA_LIFE_CAPS]
    by_life = {row["life_cap_years_scenario"]: row for row in scenarios}
    return {
        "status": "HARD_AGE_STRESS_INFEASIBLE_AT_185_ANNUAL_PURCHASES",
        "age_source": "https://data.transportation.gov/d/6abt-uhgq",
        "reported_age_bins_are_intervals": True,
        "annual_purchase_capacity": CTA_ANNUAL_CAPACITY,
        "capacity_basis": (
            "SCREENING ASSUMPTION from the legacy 1,850/10 linear pace; CTA's "
            "actual annual procurement ceiling is not in the loaded evidence."
        ),
        "selected_life_caps_years": list(CTA_LIFE_CAPS),
        "2024_due_by_life_cap": {
            life: by_life[life]["due_2024_slots"] for life in CTA_LIFE_CAPS},
        "2024_shortfall_by_life_cap": {
            life: by_life[life]["shortfall_2024_slots"] for life in CTA_LIFE_CAPS},
        "minimum_uniform_annual_capacity_by_life_cap": {
            life: by_life[life]["minimum_uniform_annual_capacity_with_2033_electrification"]
            for life in CTA_LIFE_CAPS},
        "all_selected_life_caps_feasible_at_185": all(
            row["hard_age_compliant_at_annual_capacity"] for row in scenarios),
        "initial_electric_age_allocation": (
            "UNVERIFIED; age-driven renewal of those 25 slots would add up to 25 "
            "purchases outside the 1,850 non-electric conversion lower bound."
        ),
        "scenarios": scenarios,
    }


def main() -> None:
    cta_age_model = build_cta_age_model(load_cta_age_cohorts())
    cta_age17 = next(
        x for x in cta_age_model["scenarios"]
        if x["life_cap_years_scenario"] == 17
    )
    cta_age_by_year = {x["year"]: x for x in cta_age17["annual_schedule"]}
    vancouver = json.loads((ROOT / "results/vancouver_full_fleet_bound.json").read_text())
    london = json.loads((ROOT / "results/london_cohort_roadmap.json").read_text())
    life17 = next(x for x in london["scenarios"] if x["life_cap_years_scenario"] == 17)
    london_by_year = {x["year"]: x["total_slots_renewed"] for x in life17["annual_schedule"]}
    cta_total, cta_electric = CTA_FLEET, CTA_INITIAL_ELECTRIC
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
                        "chicago_age_due_slots_17y": cta_age_by_year[row["year"]]["age_due_slots"],
                        "chicago_overdue_slots_after_year_17y": cta_age_by_year[row["year"]]["overdue_age_slots_after_year"],
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
                    f"{x['london_non_electric_remaining']}" + EOL)
    rows += [r"\midrule",
             f"Total & {sum(x['vancouver_electric_vehicle_purchases'] for x in records)} & "
             f"{records[-1]['vancouver_electric_stock_end']} & {records[-1]['vancouver_conventional_stock_end']} & "
             f"{cta_fossil} & {records[-1]['chicago_non_electric_remaining']} & "
             f"{sum(london_by_year.values())} & {records[-1]['london_non_electric_remaining']}" + "\\\\",
             r"\bottomrule", r"\end{tabular}",
             r"\caption{Annual stock-flow comparison. Vancouver's 1,909 electric purchases comprise an assumed 1,647 route positions plus 262 common trolley renewals. Chicago's CTA buy column is the legacy 1,850/10 linear arithmetic, retained only for comparison: its separate age test below shows a 2024 hard-deadline shortfall. TfL renews body-compatible slots under its 17-year scenario. Zero 2033 stock arithmetic is not a route, garage or charging certificate.}", r"\end{table}"]
    (ROOT / "paper/tables/three_city_roadmap.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    age_rows = [r"\begin{table}[htbp]", r"\centering",
                r"\begin{tabular}{@{}rrrrr@{}}", r"\toprule",
                r"Year & Age-due slots & On-time new due & Newly missed & Overdue after year\\",
                r"\midrule"]
    for row in cta_age17["annual_schedule"]:
        age_rows.append(
            f"{row['year']} & {row['age_due_slots']} & "
            f"{row['on_time_replacements_assigned_to_new_deadline']} & "
            f"{row['newly_due_slots_missed_in_year']} & "
            f"{row['overdue_age_slots_after_year']}" + EOL)
    age_rows += [r"\bottomrule", r"\end{tabular}",
                 r"\caption{Chicago 17-year hard-age stress under the unverified 185-bus/year capacity. The 539 vehicles in the oldest bins exceed 2024 capacity by 354 immediately. Clearing later backlog cannot undo that missed deadline. Bins are reported age intervals, so oldest-age deadlines are a robust stress rather than a vehicle register.}",
                 r"\label{tab:chicago_age}",
                 r"\end{table}"]
    (ROOT / "paper/tables/chicago_age_roadmap.tex").write_text(
        "\n".join(age_rows) + "\n", encoding="utf-8")
    output = {"status": "TRANSFER_PLANNING_POSITIONS_NOT_DELIVERIES",
              "vancouver": {"basis": "class-specific aggregate core envelope; 300-km duty screen",
                            "initial_stock": vancouver["initial_stock_2023"],
                            "endpoint": vancouver["endpoint_2033"]},
              "chicago": {"basis": "2023 year-end inventory; 25 inferred electric slots; legacy linear column plus hard-age cohort stress", "fleet": cta_total,
                          "initial_electric": cta_electric, "non_electric": cta_fossil, "annual": cta_annual,
                          "linear_inventory_reference": {
                              "annual_replacements": cta_annual,
                              "scope": "Legacy table continuity only; not a hard-lifespan certificate."},
                          "age_constrained_replacement_model": cta_age_model},
              "london": {"basis": "31 March 2023 audit; 17-year chassis-life cohort scenario", "fleet": 8643,
                         "initial_electric": 950, "non_electric": 7693,
                         "total_renewals": sum(london_by_year.values()), "peak_annual_renewals": max(london_by_year.values())},
              "endpoint_2033": {
                  "vancouver_conventional": records[-1]["vancouver_conventional_stock_end"],
                  "chicago_conventional": records[-1]["chicago_non_electric_remaining"],
                  "london_conventional": records[-1]["london_non_electric_remaining"],
              },
              "annual_plan": records,
              "endpoint_scope": "The 2033 zero-conventional endpoints are legacy linear inventory arithmetic. Chicago's hard-age scenarios show that 185 purchases per year fail before that endpoint is reached.",
              "chicago_17y_age_schedule": cta_age17["annual_schedule"],
              "limits": ["Vancouver active block requests include extra sequential duties but not standby/spare buses.",
                         "Chicago electric stock is inferred from a June announcement. Its 185/year linear column is retained for continuity, while the age-constrained model exposes the missed hard deadlines.",
                         "Chicago age bins do not identify individual build years or which 25 buses are electric; the robust deadlines use the oldest possible age in each bin and additional electric-slot renewals remain unverified.",
                         "London renewals retain body-type availability by cohort; this is not a route forecast.",
                         "Local vehicle prices, tariffs and station constraints remain necessary before financial comparison across cities."]}
    (ROOT / "results/three_city_roadmap.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"],
                      "vancouver_endpoint": output["vancouver"]["endpoint"],
                      "chicago_endpoint": records[-1]["chicago_non_electric_remaining"],
                      "chicago_hard_age_feasible_at_185": cta_age_model[
                          "all_selected_life_caps_feasible_at_185"],
                      "chicago_2024_shortfall_by_life_cap": cta_age_model[
                          "2024_shortfall_by_life_cap"],
                      "london_endpoint": records[-1]["london_non_electric_remaining"]}, indent=2))


if __name__ == "__main__":
    main()
