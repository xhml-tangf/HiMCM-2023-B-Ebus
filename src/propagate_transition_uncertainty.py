"""Cartesian uncertainty propagation for the conditional Vancouver case.

This is an assumption-space audit, not a statistical confidence interval. Each
cell gives equal weight; the source-labelled bounds are varied together so the
reported spread shows how much the conditional score depends on unresolved
inputs. Fleet and block units remain distinct.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data/processed"
RESULTS = ROOT / "results"
TABLES = ROOT / "paper/tables"
FIGURES = ROOT / "paper/figures"


def quantiles(values: np.ndarray) -> dict[str, float]:
    q = np.quantile(values, [0.05, 0.50, 0.95])
    return {
        "p05": float(q[0]),
        "median": float(q[1]),
        "p95": float(q[2]),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
    }


def main() -> None:
    audit = json.loads((RESULTS / "vancouver_block_range_audit.json").read_text())
    named = json.loads((RESULTS / "vancouver_transition_scenarios.json").read_text())
    weekday = next(d for d in audit["days"] if d["kind"] == "weekday")

    ranges40 = {
        x["range_km"]: x["fleet_blocks_after_ceiling"]
        for x in weekday["range_scenarios"] if x["scenario"] == "40ft"
    }
    ranges60 = {
        x["range_km"]: x["fleet_blocks_after_ceiling"]
        for x in weekday["range_scenarios"] if x["scenario"] == "60ft"
    }
    candidates40 = {
        x["range_km"]: x["battery_candidate_blocks"]
        for x in weekday["range_scenarios"] if x["scenario"] == "40ft"
    }
    candidates60 = {
        x["range_km"]: x["battery_candidate_blocks"]
        for x in weekday["range_scenarios"] if x["scenario"] == "60ft"
    }
    paired_ranges = [(149, 150), (170, 171), (184, 185),
                     (203, 205), (250, 251), (300, 300), (350, 350)]
    range_requests = np.array([ranges40[a] + ranges60[b] for a, b in paired_ranges], dtype=float)
    range_midpoints = np.array([(a + b) / 2 for a, b in paired_ranges])
    base_requests = candidates40[149] + candidates60[150]

    fleet_total = np.arange(1711, 1734)
    existing_beb = np.arange(5, 19)
    renewal_numerators = np.arange(9, 12)  # 9/17, 10/17, 11/17
    discount_rates = np.arange(0.015, 0.0501, 0.005)
    cost_bases = np.array([0, 1])  # 0: hardware screen; 1: project envelopes
    fuel_intensities_kg_per_km = np.array([0.302, 0.960, 1.233, 1.580])

    grid = np.meshgrid(
        fleet_total,
        np.arange(len(paired_ranges)),
        existing_beb,
        renewal_numerators,
        discount_rates,
        cost_bases,
        fuel_intensities_kg_per_km,
        indexing="ij",
    )
    (fleet, range_idx, beb_existing, renew_n, rate,
     cost_basis, fuel_kg_per_km) = [x.ravel() for x in grid]

    non_trolley = fleet - 262.0
    nondeck_fleet = non_trolley - 57.0  # 57 inferred 2023 double-deck buses
    plan_requests = range_requests[range_idx.astype(int)]
    plan_positions = np.floor(nondeck_fleet * plan_requests / base_requests + 0.5)
    net_new = plan_positions - beb_existing
    fossil_fleet = nondeck_fleet - beb_existing
    baseline_purchases = np.floor(fossil_fleet * renew_n / 17.0 + 0.5)

    annual_bus_km = float(named["service_baseline"]["annual_2023_bus_km"])
    base_fossil_km = float(named["service_baseline"]["annual_nondeck_fossil_km_estimate"])
    base_fossil_fleet = 1406.0 - 18.0
    annual_fossil_km = base_fossil_km * fossil_fleet / base_fossil_fleet

    conventional_unit = 46_143_000.0 / 50.0
    hardware_unit = 1_200_000.0
    project_standard = 106_846_000.0 / 57.0
    project_articulated = 3_037_000.0
    standard40 = np.array([ranges40[a] for a, _ in paired_ranges], dtype=float)[range_idx.astype(int)]
    standard_share = standard40 / plan_requests
    project_unit = standard_share * project_standard + (1 - standard_share) * project_articulated
    plan_unit = np.where(cost_basis == 1, project_unit, hardware_unit)
    infrastructure = net_new * (500_000_000.0 / 340.0)

    years = np.arange(2024, 2034)
    q, rem = np.divmod(net_new.astype(int), 10)
    base_q, base_rem = np.divmod(baseline_purchases.astype(int), 10)
    plan_capex = np.zeros_like(net_new, dtype=float)
    base_capex = np.zeros_like(net_new, dtype=float)
    plan_residual_factor = np.zeros_like(net_new, dtype=float)
    base_residual_factor = np.zeros_like(net_new, dtype=float)
    for i, year in enumerate(years):
        disc = 1.0 / (1.0 + rate) ** (year - 2023)
        plan_count = q + (i < rem)
        base_count = base_q + (i < base_rem)
        plan_capex += plan_unit * plan_count * disc
        base_capex += conventional_unit * base_count * disc
        age = 2033 - year
        residual_fraction = max(0.0, (17 - age) / 17)
        plan_residual_factor += plan_count * residual_fraction
        base_residual_factor += base_count * residual_fraction
    horizon_discount = 1.0 / (1.0 + rate) ** 10
    plan_residual = plan_unit * plan_residual_factor * horizon_discount
    base_residual = conventional_unit * base_residual_factor * horizon_discount
    infra_disc = sum(1.0 / (1.0 + rate) ** i for i in range(1, 9)) / 8.0
    plan_infrastructure_pv = infrastructure * infra_disc

    om_weight = np.zeros_like(rate, dtype=float)
    for i, year in enumerate(years, start=1):
        om_weight += ((1 - i / 10) * 2.77 + (i / 10) * 2.28) / (1.0 + rate) ** (year - 2023)
    annuity = sum(1.0 / (1.0 + rate) ** (year - 2023) for year in years)
    baseline_om = annual_fossil_km * 2.77 * annuity
    plan_om = annual_fossil_km * om_weight
    baseline_gross = base_capex + baseline_om - base_residual
    plan_gross = plan_capex + plan_infrastructure_pv + plan_om - plan_residual
    economic_score = 100.0 * (baseline_gross - plan_gross) / baseline_gross

    diesel_production_t = (6.6 * 11_429 + 0.0) / 1000.0
    beb_production_t = (6.6 * 14_880 + 58 * 335) / 1000.0
    baseline_production = baseline_purchases * diesel_production_t
    plan_production = net_new * beb_production_t
    baseline_operating = annual_fossil_km * 10 * fuel_kg_per_km / 1000.0
    plan_operating = annual_fossil_km * 10 * 0.019 / 1000.0
    baseline_maintenance = annual_fossil_km * 10 * 0.0524 / 1000.0
    plan_maintenance = annual_fossil_km * 10 * 0.0675 / 1000.0
    baseline_emissions = baseline_production + baseline_operating + baseline_maintenance
    plan_emissions = plan_production + plan_operating + plan_maintenance
    environment_score = 100.0 * (baseline_emissions - plan_emissions) / baseline_emissions

    base_case = next(x for x in named["economics"] if x["case"] == "central")
    named_env_case = next(x for x in named["environment"] if x["case"] == "weighted_mix")
    inputs = {
        "derived_2023_fleet_total": fleet,
        "paired_range_midpoint_km": range_midpoints[range_idx.astype(int)],
        "existing_beb_retained": beb_existing,
        "natural_renewal_fraction": renew_n / 17.0,
        "discount_rate": rate,
        "project_envelope_cost_basis": cost_basis,
        "baseline_fuel_intensity_kg_co2e_km": fuel_kg_per_km,
        "net_new_battery_positions": net_new,
    }

    def impacts(outcome: np.ndarray) -> dict[str, float]:
        ranked_y = rankdata(outcome, method="average")
        values = {}
        for key, x in inputs.items():
            ranked_x = rankdata(x, method="average")
            values[key] = float(np.corrcoef(ranked_x, ranked_y)[0, 1])
        return values

    summary = {
        "status": "EXECUTED_CARTESIAN_ASSUMPTION_SPACE_NOT_A_CONFIDENCE_INTERVAL",
        "cells": int(economic_score.size),
        "grid": {
            "fleet_2023_total": {"min": 1711, "max": 1733, "step": 1, "count": 23},
            "paired_range_midpoints_km": range_midpoints.tolist(),
            "existing_beb_retained": [5, 18, 1],
            "natural_renewal_fraction_numerators_over_17": renewal_numerators.tolist(),
            "discount_rates": discount_rates.tolist(),
            "vehicle_cost_bases": {"0": "CAD 1.2m hardware screen", "1": "CAD 1.874m/3.037m project envelopes"},
            "baseline_fuel_intensity_kg_co2e_km": fuel_intensities_kg_per_km.tolist(),
        },
        "named_base_case": {
            "gross_pv_cad": base_case["plan_gross_pv_cad"],
            "economic_score_pct": base_case["economic_score_gross_pct"],
        },
        "gross_pv_cad": quantiles(plan_gross),
        "economic_score_pct": quantiles(economic_score),
        "environment_score_pct": quantiles(environment_score),
        "gross_pv_rank_correlations": impacts(plan_gross),
        "economic_score_rank_correlations": impacts(economic_score),
        "environment_rank_correlations": impacts(environment_score),
        "quantile_weighting": "Equal weight across the Cartesian assumption grid; quantiles are not sampling confidence intervals.",
        "boundaries": [
            "Infrastructure uses the named CAD 500m/340 Marpole screening ratio; the separate CAD 6.52bn expansion envelope is not mixed into this grid.",
            "Active block requests are not a garage roster; standby buses and unverified site power are outside this propagation.",
            "The emissions boundary is a partial production/operation/maintenance inventory and excludes depot construction and end-of-life.",
        ],
    }
    named_mask = (
        (fleet == 1725) & (range_midpoints[range_idx.astype(int)] == 300)
        & (beb_existing == 18) & (renew_n == 10) & np.isclose(rate, 0.03)
        & (cost_basis == 0) & np.isclose(fuel_kg_per_km, 1.233)
    )
    summary["named_case_grid_reproduction"] = {
        "cases_matched": int(named_mask.sum()),
        "net_new_battery_positions": float(net_new[named_mask][0]),
        "gross_pv_difference_cad": float(plan_gross[named_mask][0] - base_case["plan_gross_pv_cad"]),
        "economic_score_difference_pct_points": float(economic_score[named_mask][0] - base_case["economic_score_gross_pct"]),
        "environment_score_difference_pct_points": float(environment_score[named_mask][0] - named_env_case["environment_score_boundary_pct"]),
    }
    RESULTS.joinpath("vancouver_transition_uncertainty.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    frame = pd.DataFrame({
        "fleet_2023_total": fleet,
        "range_midpoint_km": range_midpoints[range_idx.astype(int)],
        "existing_beb_retained": beb_existing,
        "natural_renewal_fraction": renew_n / 17.0,
        "discount_rate": rate,
        "project_envelope_cost_basis": cost_basis,
        "baseline_fuel_kg_per_km": fuel_kg_per_km,
        "net_new_battery_positions": net_new,
        "plan_gross_pv_cad": plan_gross,
        "economic_score_pct": economic_score,
        "environment_score_pct": environment_score,
    })
    frame.to_csv(PROC / "vancouver_transition_uncertainty_grid.csv.gz", index=False,
                 compression="gzip")

    eco = summary["economic_score_pct"]
    env = summary["environment_score_pct"]
    rows = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Output & Named case & 5th pct. & Median & 95th pct. \\",
        r"\midrule",
        f"Electric gross PV (CAD bn) & {base_case['plan_gross_pv_cad']/1e9:.2f} & {summary['gross_pv_cad']['p05']/1e9:.2f} & {summary['gross_pv_cad']['median']/1e9:.2f} & {summary['gross_pv_cad']['p95']/1e9:.2f} \\\\",
        f"Economic score (\\%) & {base_case['economic_score_gross_pct']:.1f} & {eco['p05']:.1f} & {eco['median']:.1f} & {eco['p95']:.1f} \\\\",
        f"Environment score (\\%) & {named_env_case['environment_score_boundary_pct']:.1f} & {env['p05']:.1f} & {env['median']:.1f} & {env['p95']:.1f} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        f"\\caption{{Executed uncertainty propagation over {economic_score.size:,} source-bounded cases. Quantiles weight every grid cell equally; they are not statistical confidence intervals. The vehicle basis, retained stock, range, renewal rate, discount rate and baseline fuel mix vary. The named CAD 6.52-billion expansion envelope is excluded.}}",
        r"\end{table}",
    ]
    TABLES.joinpath("vancouver_uncertainty.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")

    print(json.dumps({k: summary[k] for k in (
        "cells", "gross_pv_cad", "economic_score_pct", "environment_score_pct",
        "economic_score_rank_correlations")}, indent=2))


if __name__ == "__main__":
    main()
