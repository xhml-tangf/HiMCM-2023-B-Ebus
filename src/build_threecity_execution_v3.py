"""Build fleet-class execution certificates for Chicago and London.

This is an isolated follow-up to the three-city roadmap. It does not claim
route-level service certificates. Chicago is tested against the purchase and
overhaul envelopes printed in its 2024 budget. London is rebuilt from the
31-March-2023 TfL registration/body/propulsion audit.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

try:
    from .optimize_london_cohorts import load_cohorts, solve as solve_london
except ImportError:
    from optimize_london_cohorts import load_cohorts, solve as solve_london

ROOT = Path(__file__).resolve().parents[1]
YEARS = list(range(2024, 2034))

CTA_FLEET = 1875
CTA_STANDARD = 1576
CTA_ARTICULATED = 299
CTA_INITIAL_BEB = 25
# CTA 2024 budget, Bus Fleet Management Plan narrative (PDF pp. 63 and 66):
# 40-ft: 457 (2023--26) + 700 (2027--33); 60-ft: 140 (2023--26) + 170
# (2027--29). These are "up to" purchase envelopes, not bids.
CTA_FMP_STANDARD = 457 + 700
CTA_FMP_ARTICULATED = 140 + 170
CTA_FMP_2023_26 = 457 + 140
CTA_2024_DELIVERY_BUSES = 200
CTA_FUNDED_1000_EXTENSIONS = 430
CTA_FMP_MAX_EXTENSIONS = 608


def load_cta_age_cohorts() -> list[dict]:
    rows = []
    path = ROOT / "data/processed/cta_2023_age_cohorts.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append({"vehicle_type": raw["vehicle_type"],
                         "age_low": int(raw["age_low"]),
                         "age_high": int(raw["age_high"]),
                         "vehicles": int(raw["vehicles"])})
    assert sum(r["vehicles"] for r in rows) == CTA_FLEET
    assert sum(r["vehicles"] for r in rows if r["vehicle_type"] == "Bus") == CTA_STANDARD
    assert sum(r["vehicles"] for r in rows if r["vehicle_type"] == "Articulated Bus") == CTA_ARTICULATED
    return rows


def _known_beb_due_year(life_cap: int) -> int:
    # Two CTA 40-ft BEBs entered service in 2014 (2024 budget PDF p. 66).
    deadline = 2014 + life_cap
    return deadline if deadline <= 2033 else 2034


def cta_due_schedule(cohorts: list[dict], life_cap: int,
                     extend_1000_series: int = 0) -> dict[str, dict[int, int]]:
    """Robust oldest-age deadlines and an explicit 1000-series extension case."""
    due = {"Bus": {year: 0 for year in YEARS},
           "Articulated Bus": {year: 0 for year in YEARS}}
    for row in cohorts:
        deadline = max(2024, 2023 + life_cap - row["age_high"])
        if deadline <= 2033:
            due[row["vehicle_type"]][deadline] += row["vehicles"]
    # The age table does not identify which slots are BEBs. The two 2014 buses
    # are known; the 23 2022 buses cannot reach any selected cap by 2033.
    beb_year = _known_beb_due_year(life_cap)
    if beb_year in due["Bus"]:
        if due["Bus"][beb_year] < 2:
            raise ValueError("Known 2014 BEBs are not represented in the due bin")
        due["Bus"][beb_year] -= 2
    if extend_1000_series:
        if life_cap != 14:
            raise ValueError("The funded 1000-series extension is modeled under CTA's 14-year plan")
        moved = min(int(extend_1000_series), due["Bus"][2024])
        due["Bus"][2024] -= moved
        # Funded work says service through 2028/29; use the later boundary.
        due["Bus"][2029] += moved
    return due


def solve_cta_conversion_schedule(cohorts: list[dict], life_cap: int,
                                  extend_1000_series: int = 0) -> dict:
    """Minimum-peak, latest-feasible non-electric replacement batches.

    Targets are fleet slots: 1,551 non-electric standard buses and 299
    non-electric articulated buses. The two known 2014 BEBs are renewed in
    their age deadline but are not part of the non-electric target.
    """
    due = cta_due_schedule(cohorts, life_cap, extend_1000_series)
    target = {"Bus": CTA_STANDARD - CTA_INITIAL_BEB,
              "Articulated Bus": CTA_ARTICULATED}
    ev_year = _known_beb_due_year(life_cap)
    ev_renewals = {year: (2 if year == ev_year else 0) for year in YEARS}
    cumulative_due = {kind: 0 for kind in target}
    cumulative_ev = 0
    lower_peak = math.ceil((sum(target.values()) + 2) / len(YEARS))
    for index, year in enumerate(YEARS, start=1):
        cumulative_due = {kind: cumulative_due[kind] + due[kind][year]
                          for kind in target}
        cumulative_ev += ev_renewals[year]
        lower_peak = max(lower_peak, math.ceil(
            (sum(cumulative_due.values()) + cumulative_ev) / index))

    # Twenty purchase variables. A fixed peak cap makes the schedule explicit;
    # a negative year weight back-loads purchases that deadlines do not force.
    variables = [(kind, year) for kind in target for year in YEARS]
    size = len(variables)
    rows, lower, upper = [], [], []
    matrix = lil_matrix((len(target) * len(YEARS) + len(YEARS) + len(target), size))
    row = 0
    for kind in target:
        running = 0
        for j, year in enumerate(YEARS):
            running += due[kind][year]
            for k, (var_kind, var_year) in enumerate(variables):
                if var_kind == kind and var_year <= year:
                    matrix[row, k] = 1
            lower.append(running)
            upper.append(np.inf)
            row += 1
    for year_index, year in enumerate(YEARS):
        for k, (_, var_year) in enumerate(variables):
            if var_year == year:
                matrix[row, k] = 1
        lower.append(0)
        upper.append(lower_peak - ev_renewals[year])
        row += 1
    for kind in target:
        for k, (var_kind, _) in enumerate(variables):
            if var_kind == kind:
                matrix[row, k] = 1
        lower.append(target[kind])
        upper.append(target[kind])
        row += 1
    objective = np.array([-(year - 2023) for _, year in variables], dtype=float)
    result = milp(objective, integrality=np.ones(size),
                  bounds=Bounds(np.zeros(size), np.full(size, CTA_FLEET)),
                  constraints=LinearConstraint(matrix.tocsr(), lower, upper),
                  options={"time_limit": 60, "mip_rel_gap": 0})
    if result.status != 0:
        raise RuntimeError(result.message)
    values = np.rint(result.x).astype(int)
    assert np.max(np.abs(values - result.x)) < 1e-6
    purchased = {kind: {year: 0 for year in YEARS} for kind in target}
    for value, (kind, year) in zip(values, variables):
        purchased[kind][year] = int(value)
    cumulative_std = cumulative_art = 0
    annual = []
    for year in YEARS:
        cumulative_std += purchased["Bus"][year]
        cumulative_art += purchased["Articulated Bus"][year]
        cumulative_due_std = sum(due["Bus"][y] for y in YEARS if y <= year)
        cumulative_due_art = sum(due["Articulated Bus"][y] for y in YEARS if y <= year)
        assert cumulative_std >= cumulative_due_std
        assert cumulative_art >= cumulative_due_art
        annual.append({
            "year": year,
            "standard_due_slots": due["Bus"][year],
            "articulated_due_slots": due["Articulated Bus"][year],
            "standard_non_electric_replacements": purchased["Bus"][year],
            "articulated_non_electric_replacements": purchased["Articulated Bus"][year],
            "known_2014_beb_renewals": ev_renewals[year],
            "total_purchases": (purchased["Bus"][year]
                                + purchased["Articulated Bus"][year]
                                + ev_renewals[year]),
            "non_electric_slots_remaining": (
                sum(target.values()) - cumulative_std - cumulative_art),
        })
    assert cumulative_std == target["Bus"]
    assert cumulative_art == target["Articulated Bus"]
    assert annual[-1]["non_electric_slots_remaining"] == 0
    assert max(x["total_purchases"] for x in annual) <= lower_peak
    return {
        "life_cap_years": life_cap,
        "funded_1000_series_life_extensions": extend_1000_series,
        "minimum_peak_annual_purchases": lower_peak,
        "minimum_total_purchases_with_known_beb_renewals": (
            sum(target.values()) + 2),
        "non_electric_target_by_type": target,
        "2024_due_before_extensions": sum(cta_due_schedule(cohorts, life_cap)[k][2024]
                                           for k in target),
        "2024_due_after_extensions": sum(due[k][2024] for k in target),
        "schedule": annual,
        "solver_status": "OPTIMAL",
        "mip_gap": float(result.mip_gap),
        "note": ("Oldest-age robust deadlines; the 430/608 extension is applied "
                 "to 14+-year standard 1000-series slots and is an optimistic "
                 "2024 deferral because the public age bins do not identify vehicles."),
    }


def build_cta_certificate() -> dict:
    cohorts = load_cta_age_cohorts()
    scenarios = [solve_cta_conversion_schedule(cohorts, life) for life in (12, 14, 17)]
    funded = solve_cta_conversion_schedule(cohorts, 14, CTA_FUNDED_1000_EXTENSIONS)
    max_extended = solve_cta_conversion_schedule(cohorts, 14, CTA_FMP_MAX_EXTENSIONS)
    needed_standard = CTA_STANDARD - CTA_INITIAL_BEB
    needed_articulated = CTA_ARTICULATED
    needed_total = needed_standard + needed_articulated
    known_beb_renews = 2
    standard_shortfall = needed_standard + known_beb_renews - CTA_FMP_STANDARD
    articulated_spare = CTA_FMP_ARTICULATED - needed_articulated
    total_shortfall = (needed_total + known_beb_renews
                       - (CTA_FMP_STANDARD + CTA_FMP_ARTICULATED))
    return {
        "status": "INFEASIBLE_AGAINST_CURRENT_OFFICIAL_FMP_ENVELOPE_AND_2024_RAMP",
        "fleet_basis": {
            "year_end_2023_slots": CTA_FLEET,
            "standard": CTA_STANDARD,
            "articulated": CTA_ARTICULATED,
            "current_standard_40ft_bebs": CTA_INITIAL_BEB,
            "current_bebs_2014": 2,
            "current_bebs_2022": 23,
        },
        "official_fmp_purchase_envelope": {
            "standard_40ft": CTA_FMP_STANDARD,
            "articulated_60ft": CTA_FMP_ARTICULATED,
            "total": CTA_FMP_STANDARD + CTA_FMP_ARTICULATED,
            "2023_26_standard_plus_articulated": CTA_FMP_2023_26,
            "source": "CTA FY2024 Proposed Budget, Bus Fleet Management Plan, PDF p. 63",
            "warning": ("Up-to period envelopes, not annual deliveries. The 1,467 "
                        "is already generous because some 2023 purchases are in the "
                        "year-end 2023 inventory."),
        },
        "2033_electrification_shortfall_under_fmp": {
            "non_electric_standard_to_replace": needed_standard,
            "known_age_due_2014_beb_renewals": known_beb_renews,
            "standard_purchase_shortfall": standard_shortfall,
            "non_electric_articulated_to_replace": needed_articulated,
            "articulated_envelope_surplus": articulated_spare,
            "total_minimum_purchases": needed_total + known_beb_renews,
            "total_purchase_shortfall": total_shortfall,
            "outer_beb_age_uncertainty_purchase_range": [needed_total, CTA_FLEET],
        },
        "2024_ramp_certificate": {
            "known_2024_new_bus_deliveries_in_budget": CTA_2024_DELIVERY_BUSES,
            "due_at_14_year_cap_no_extension": funded["2024_due_before_extensions"],
            "due_after_430_funded_life_extensions": funded["2024_due_after_extensions"],
            "due_after_608_fmp_max_life_extensions": max_extended["2024_due_after_extensions"],
            "shortfall_after_430_vs_200_budgeted_deliveries": (
                funded["2024_due_after_extensions"] - CTA_2024_DELIVERY_BUSES),
            "shortfall_after_608_vs_200_budgeted_deliveries": (
                max_extended["2024_due_after_extensions"] - CTA_2024_DELIVERY_BUSES),
            "entire_2023_26_purchase_envelope_vs_2024_due_after_430": (
                CTA_FMP_2023_26 - funded["2024_due_after_extensions"]),
            "note": ("The 200 deliveries are a budget statement, not a typed, "
                     "dated completion certificate; they still expose a ramp gap."),
        },
        "stress_scenarios_without_life_extension": scenarios,
        "funded_life_extension_schedule": funded,
        "fmp_maximum_extension_schedule": max_extended,
        "residual_limits": [
            "No public vehicle ID register, so the 25 BEB ages are inferred only from the two 2014 and twenty-three 2022 purchases.",
            "No route block, depot, charger or firm-power data are used in this Chicago certificate.",
            "The conclusion is against the current published FMP envelope and 2024 ramp; a larger procurement plan can change it.",
        ],
    }


def _body(kind: str) -> str:
    if kind.startswith("single"):
        return "single_deck"
    if kind.startswith("double"):
        return "double_deck"
    raise ValueError(kind)


def summarize_london(scenario: dict) -> dict:
    conversions = defaultdict(Counter)
    renewals = defaultdict(Counter)
    for item in scenario["cohort_assignments"]:
        body = _body(item["kind"])
        action = "renewal" if item["electric"] else "conversion"
        (renewals if action == "renewal" else conversions)[item["year"]][body] += item["slots"]
    annual = []
    remaining = {"single_deck": 2083, "double_deck": 5610}
    max_single = max_double = 0
    hydrogen_by_year = Counter()
    for item in scenario["cohort_assignments"]:
        if item["kind"] == "double_hydrogen":
            hydrogen_by_year[item["year"]] += item["slots"]
    for row in scenario["annual_schedule"]:
        year = row["year"]
        single = conversions[year]["single_deck"]
        double = conversions[year]["double_deck"]
        single_renewal = renewals[year]["single_deck"]
        double_renewal = renewals[year]["double_deck"]
        remaining["single_deck"] -= single
        remaining["double_deck"] -= double
        assert remaining["single_deck"] >= 0 and remaining["double_deck"] >= 0
        total = single + double + single_renewal + double_renewal
        assert total == row["total_slots_renewed"]
        assert row["single_deck_slots"] == single + single_renewal
        assert row["double_deck_slots"] == double + double_renewal
        max_single = max(max_single, single + single_renewal)
        max_double = max(max_double, double + double_renewal)
        annual.append({
            "year": year,
            "single_deck_non_electric_conversions": single,
            "double_deck_non_electric_conversions": double,
            "single_deck_existing_electric_renewals": single_renewal,
            "double_deck_existing_electric_renewals": double_renewal,
            "total_new_electric_deliveries": total,
            "remaining_non_electric_single_deck": remaining["single_deck"],
            "remaining_non_electric_double_deck": remaining["double_deck"],
            "remaining_non_electric_total": sum(remaining.values()),
        })
    assert remaining == {"single_deck": 0, "double_deck": 0}
    assert sum(hydrogen_by_year.values()) == 20
    assert max(x["total_new_electric_deliveries"] for x in annual) <= scenario["minimum_peak_annual_slot_renewal"]
    return {
        "life_cap_years": scenario["life_cap_years_scenario"],
        "minimum_peak_annual_new_electric_deliveries": scenario["minimum_peak_annual_slot_renewal"],
        "analytic_cumulative_deadline_bound": scenario["analytic_cumulative_deadline_bound"],
        "non_electric_conversions_by_body": {"single_deck": 2083,
                                             "double_deck": 5610},
        "existing_electric_renewals_by_body": {
            "single_deck": sum(x["single_deck_existing_electric_renewals"] for x in annual),
            "double_deck": sum(x["double_deck_existing_electric_renewals"] for x in annual),
        },
        "minimum_total_new_electric_deliveries": scenario["total_slots_renewed"],
        "maximum_annual_single_deck_deliveries": max_single,
        "maximum_annual_double_deck_deliveries": max_double,
        "hydrogen_double_deck_converted_by_year": dict(sorted(hydrogen_by_year.items())),
        "strict_electric_body_class_certificate": True,
        "route_or_charging_certificate": False,
        "solver_status": scenario["solver_status"],
        "phase_mip_gaps": scenario["phase_mip_gaps"],
        "annual_plan": annual,
        "procurement_batches": scenario["cohort_assignments"],
    }


def build_london_certificate() -> dict:
    base = load_cohorts()
    body_totals = Counter()
    electric = Counter()
    for row in base:
        body_totals[_body(row["kind"])] += row["count"]
        if row["electric"]:
            electric[_body(row["kind"])] += row["count"]
    assert body_totals == {"single_deck": 2445, "double_deck": 6198}
    assert electric == {"single_deck": 362, "double_deck": 588}
    scenarios = [summarize_london(solve_london(life)) for life in (12, 14, 17)]
    return {
        "status": "FLEET_CLASS_BODY_COMPATIBLE_PLAN_EXECUTABLE; ROUTE_DEPOT_CHARGING_UNVERIFIED",
        "source": "TfL Bus Fleet Audit, 31 March 2023, detailed registration/body tables",
        "fleet_basis": {
            "total_slots": 8643,
            "single_deck": 2445,
            "double_deck": 6198,
            "audited_electric_single_deck": 362,
            "audited_electric_double_deck": 588,
            "audited_hydrogen_double_deck_reclassified_for_strict_electric_endpoint": 20,
            "non_electric_single_deck": 2083,
            "non_electric_double_deck": 5610,
        },
        "plan_interpretation": ("One like-body electric bus replaces each non-electric fleet slot; "
                                "existing electric slots due under the selected life cap are renewed. "
                                "This is an order-batch plan at body-class level, not a route or garage plan."),
        "scenarios": scenarios,
        "residual_limits": [
            "Route-to-vehicle assignments and the required spare fleet are not in the audit.",
            "Depot charging capacity, site power, delivery lead times and local prices are absent.",
            "Life caps are sensitivity scenarios, not asserted TfL retirement rules.",
            "The 2024 catch-up must be paired with facility-ready garages before it is operationally executable.",
        ],
    }


def main() -> None:
    chicago = build_cta_certificate()
    london = build_london_certificate()
    output = {
        "date": "2026-10-20",
        "status": "TWO_CITY_FLEET_CLASS_EXECUTION_CERTIFICATES_COMPLETED",
        "chicago": chicago,
        "london": london,
        "shared_boundary": ("These certificates establish vehicle-body and age stock flows only. "
                            "They do not establish route-level service preservation or charging feasibility."),
    }
    path = ROOT / "results/threecity_execution_certificates_v3.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    batch_rows = []
    cta_plans = [*chicago["stress_scenarios_without_life_extension"],
                 chicago["funded_life_extension_schedule"],
                 chicago["fmp_maximum_extension_schedule"]]
    seen_cta = set()
    for plan in cta_plans:
        key = (plan["life_cap_years"], plan["funded_1000_series_life_extensions"])
        if key in seen_cta:
            continue
        seen_cta.add(key)
        for row in plan["schedule"]:
            for body, column in (("40ft_standard", "standard_non_electric_replacements"),
                                 ("60ft_articulated", "articulated_non_electric_replacements")):
                if row[column]:
                    batch_rows.append({"city": "Chicago", "life_cap_years": plan["life_cap_years"],
                                       "extension_units": plan["funded_1000_series_life_extensions"],
                                       "year": row["year"], "body_type": body,
                                       "vintage": "", "action": "non_electric_conversion",
                                       "units": row[column]})
            if row["known_2014_beb_renewals"]:
                batch_rows.append({"city": "Chicago", "life_cap_years": plan["life_cap_years"],
                                   "extension_units": plan["funded_1000_series_life_extensions"],
                                   "year": row["year"], "body_type": "40ft_standard",
                                   "vintage": 2014, "action": "existing_electric_renewal",
                                   "units": row["known_2014_beb_renewals"]})
    for scenario in london["scenarios"]:
        for item in scenario["procurement_batches"]:
            batch_rows.append({"city": "London", "life_cap_years": scenario["life_cap_years"],
                               "extension_units": "", "year": item["year"],
                               "body_type": _body(item["kind"]), "vintage": item["vintage"],
                               "action": ("existing_electric_renewal" if item["electric"]
                                          else "non_electric_conversion"),
                               "units": item["slots"]})
    batch_path = ROOT / "data/processed/threecity_execution_batches_v3.csv"
    with batch_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(batch_rows[0]))
        writer.writeheader()
        writer.writerows(batch_rows)
    print(json.dumps({
        "status": output["status"],
        "chicago_total_purchase_shortfall": chicago["2033_electrification_shortfall_under_fmp"]["total_purchase_shortfall"],
        "chicago_2024_shortfall_after_430_vs_200": chicago["2024_ramp_certificate"]["shortfall_after_430_vs_200_budgeted_deliveries"],
        "london_peaks": {s["life_cap_years"]: s["minimum_peak_annual_new_electric_deliveries"] for s in london["scenarios"]},
    }, indent=2))


if __name__ == "__main__":
    main()
