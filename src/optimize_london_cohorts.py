"""Execute a fixed-availability age-cohort planning benchmark for London.

This optimizes annual *service slots renewed*, not trip-feasible bus purchases.
Like-body availability is retained; operational scheduling may require extra
electric vehicles. Service-life caps are explicit scenarios, not TfL policy.
The 2013 electric NRM is aged by chassis registration, not its 2022 retrofit.
"""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, lil_matrix, vstack

ROOT = Path(__file__).resolve().parents[1]
YEARS = list(range(2024, 2034))
SOURCE = "https://content.tfl.gov.uk/fleet-annual-audit-report-31-march-2023.pdf"


def load_cohorts() -> list[dict]:
    cohorts = []
    with (ROOT / "data/processed/london_2023_registration_cohorts.csv").open(
            newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            vintage = int(row.pop("registration_year"))
            for kind, value in row.items():
                if int(value):
                    cohorts.append({"vintage": vintage, "kind": kind,
                                    "count": int(value), "electric": kind.endswith("electric")})
    assert sum(c["count"] for c in cohorts) == 8643
    assert sum(c["count"] for c in cohorts if c["electric"]) == 950
    assert sum(c["count"] for c in cohorts if c["kind"].startswith("single")) == 2445
    assert sum(c["count"] for c in cohorts if c["kind"].startswith("double")) == 6198
    return cohorts


def solve(life_cap: int) -> dict:
    started = time.perf_counter()
    all_cohorts = load_cohorts()
    cohorts = []
    for row in all_cohorts:
        natural_due = max(2024, row["vintage"] + life_cap)
        if row["electric"] and natural_due > 2033:
            continue
        cohorts.append({**row, "deadline": min(2033, natural_due),
                        "natural_due": natural_due})
    pairs = [(i, year) for i, row in enumerate(cohorts)
             for year in YEARS if year <= row["deadline"]]
    size = len(pairs) + 1
    matrix = lil_matrix((len(cohorts) + len(YEARS), size))
    lower = np.zeros(len(cohorts) + len(YEARS))
    upper = np.zeros_like(lower)
    variable_upper = np.empty(size)
    for j, (i, year) in enumerate(pairs):
        matrix[i, j] = 1
        matrix[len(cohorts) + year - 2024, j] = 1
        variable_upper[j] = cohorts[i]["count"]
    for i, row in enumerate(cohorts):
        lower[i] = upper[i] = row["count"]
    for k in range(len(YEARS)):
        matrix[len(cohorts) + k, -1] = -1
        lower[len(cohorts) + k] = -np.inf
    variable_upper[-1] = 8643
    objective = np.zeros(size)
    objective[-1] = 1
    constraints = LinearConstraint(matrix.tocsr(), lower, upper)
    result = milp(objective, integrality=np.ones(size),
                  bounds=Bounds(np.zeros(size), variable_upper), constraints=constraints,
                  options={"time_limit": 60, "mip_rel_gap": 0})
    if result.status != 0:
        raise RuntimeError(result.message)
    peak = round(result.x[-1])
    analytic_bound = max(math.ceil(sum(c["count"] for c in cohorts
                                      if c["deadline"] <= year) / (year - 2023))
                         for year in YEARS)
    assert peak == analytic_bound
    variable_upper[-1] = peak
    # With minimum peak capacity fixed, retire each cohort as late as possible.
    objective = np.array([cohorts[i]["deadline"] - year for i, year in pairs] + [0.0])
    late_result = milp(objective, integrality=np.ones(size),
                       bounds=Bounds(np.zeros(size), variable_upper), constraints=constraints,
                       options={"time_limit": 60, "mip_rel_gap": 0})
    if late_result.status != 0:
        raise RuntimeError(late_result.message)
    # Among schedules with the same minimum peak and early-renewal exposure,
    # convert non-electric slots first rather than prematurely renewing EVs.
    best_earliness = round(late_result.fun)
    tie_matrix = vstack([matrix.tocsr(), csr_matrix(objective.reshape(1, -1))])
    tie_constraints = LinearConstraint(tie_matrix, np.r_[lower, best_earliness],
                                       np.r_[upper, best_earliness])
    climate_objective = np.array([-(2034 - year) if not cohorts[i]["electric"] else 0
                                  for i, year in pairs] + [0.0])
    final_result = milp(climate_objective, integrality=np.ones(size),
                        bounds=Bounds(np.zeros(size), variable_upper),
                        constraints=tie_constraints,
                        options={"time_limit": 60, "mip_rel_gap": 0})
    if final_result.status != 0:
        raise RuntimeError(final_result.message)
    values = np.rint(final_result.x).astype(int)
    assert np.max(np.abs(values - final_result.x)) < 1e-6
    assert abs(objective @ values - best_earliness) < 1e-6
    assignments = [{**cohorts[i], "year": year, "slots": int(values[j])}
                   for j, (i, year) in enumerate(pairs) if values[j]]
    for i, row in enumerate(cohorts):
        assert sum(values[j] for j, (index, _) in enumerate(pairs) if index == i) == row["count"]
    annual = []
    remaining_non_electric = 8643 - 950
    for year in YEARS:
        planned = [a for a in assignments if a["year"] == year]
        converted = sum(a["slots"] for a in planned if not a["electric"])
        renewed_electric = sum(a["slots"] for a in planned if a["electric"])
        remaining_non_electric -= converted
        annual.append({"year": year, "non_electric_slots_converted": converted,
                       "existing_electric_slots_renewed": renewed_electric,
                       "total_slots_renewed": converted + renewed_electric,
                       "single_deck_slots": sum(a["slots"] for a in planned
                                                if a["kind"].startswith("single")),
                       "double_deck_slots": sum(a["slots"] for a in planned
                                                if a["kind"].startswith("double")),
                       "remaining_non_electric_slots": remaining_non_electric})
        assert annual[-1]["total_slots_renewed"] <= peak
    assert remaining_non_electric == 0
    return {
        "life_cap_years_scenario": life_cap,
        "minimum_peak_annual_slot_renewal": peak,
        "analytic_cumulative_deadline_bound": analytic_bound,
        "non_electric_slots_converted": 7693,
        "existing_electric_slots_renewed": sum(a["existing_electric_slots_renewed"] for a in annual),
        "total_slots_renewed": sum(a["total_slots_renewed"] for a in annual),
        "early_renewal_slot_years_relative_to_capped_deadline": round(late_result.fun),
        "non_electric_slot_years_converted_to_electric": round(-final_result.fun),
        "early_retirement_slot_years_relative_to_life_cap": sum(
            max(0, a["natural_due"] - a["year"]) * a["slots"] for a in assignments),
        "solver_status": "OPTIMAL",
        "mip_gap": float(final_result.mip_gap),
        "phase_mip_gaps": [float(result.mip_gap), float(late_result.mip_gap),
                           float(final_result.mip_gap)],
        "solve_elapsed_seconds": time.perf_counter() - started,
        "annual_schedule": annual,
        "cohort_assignments": assignments,
    }


def main() -> None:
    scenarios = [solve(life) for life in (12, 14, 17)]
    output = {
        "status": "OPTIMAL_FIXED_AVAILABILITY_COHORT_BENCHMARK_NOT_ROUTE_CERTIFICATE",
        "source": SOURCE,
        "source_tables": "Tables 7--8 (single/double-deck); 31 March 2023",
        "fleet_slots": 8643,
        "initial_electric_slots": 950,
        "computation": {"engine": "SciPy scipy.optimize.milp / HiGHS",
                        "scipy_version": scipy.__version__,
                        "python_version": platform.python_version(),
                        "logical_cpu_count": os.cpu_count(), "device": "CPU only"},
        "note": "Life caps are sensitivity assumptions. Each renewed original fleet slot needs compatible electric capacity; actual bus quantities, spare requirements, winter heat and chargers require the separate operational validator. No financial or life-cycle score follows from this age-only model.",
        "source_internal_issue": "Table 2 prints single-deck total 2447 and 2017 single-deck 341; detailed Tables 7--8 and Table 3 instead reconcile to 2445 and 339. This dataset follows the detailed tables and published fleet total 8643.",
        "scenarios": scenarios,
    }
    (ROOT / "results/london_cohort_roadmap.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8")
    with (ROOT / "results/london_cohort_annual.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["life_cap_years_scenario"]
                                + list(scenarios[0]["annual_schedule"][0]))
        writer.writeheader()
        for scenario in scenarios:
            for row in scenario["annual_schedule"]:
                writer.writerow({"life_cap_years_scenario": scenario["life_cap_years_scenario"], **row})
    print(json.dumps([{key: value for key, value in s.items()
                       if key not in ("cohort_assignments", "annual_schedule")}
                      for s in scenarios], indent=2))


if __name__ == "__main__":
    main()
