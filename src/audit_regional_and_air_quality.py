"""Audit regional economic and bus tailpipe bounds for the Vancouver case.

This module deliberately keeps three objects separate:

1. recurring 2023 Bus Operations activity;
2. one-time transition capital activity; and
3. bus-only tailpipe pollutant emissions.

It does not treat construction expenditure as revenue, a return, or a net
benefit.  It also does not use TransLink's all-revenue-fleet CAC total because
that series cannot be decomposed into fixed-route bus modes.

Run from the repository root with::

    python src/audit_regional_and_air_quality.py

The source values are embedded with their document/table/page locators so that
the audit is reproducible offline.  The EEA workbook coefficients below are
transcribed from the July 2026 Appendix 4 workbook for the 2023 Guidebook.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Published 2023 operating, fleet, fuel, and service inputs
# ---------------------------------------------------------------------------

# TransLink 2025 Business Plan, p. 21, "Bus Operations by Category" (2023 actual).
BUS_OPERATIONS_CAD_M = 945.537
BUS_WAGES_CAD_M = 619.195

# TransLink 2023 Accountability Report, PDF p. 63: 2023, 72.5% of total spend.
BC_SUPPLIER_SPEND_SHARE = 0.725

# Transport Canada Table RO13 / Statistics Canada 23-10-0083-01, 2023P.
# Urban transit systems, average annual compensation (current CAD).
AVERAGE_ANNUAL_COMPENSATION_CAD = 102_872.0

# 2023 fixed-route bus service, source-derived revenue service km.  SeaBus,
# HandyDART and rail are excluded.
BUS_SERVICE_KM = 106_868_324.0
BUS_SERVICE_HOURS = 5_575_772.0

# 2023 natural-gas use.  Accountability Report, PDF p. 38:
# 575,495 GJ of RNG and RNG = 96% of purchased bus natural gas.
RNG_GJ_2023 = 575_495.0
RNG_SHARE_OF_NATURAL_GAS = 0.96

# 2022 detailed fleet snapshot retained by the project.  These counts are a
# stock split, not a 2023 vehicle-km register.  CNG count is confirmed as 299
# vehicles in the 2023 Accountability Report.
CNG_BUS_COUNT = 299
DIESEL_BUS_COUNT = 448
HYBRID_BUS_COUNT = 446 + 46  # CMBC hybrid plus contracted diesel-hybrid.

# TransLink 2025 Business Plan, p. 21, 2023 actual service kilometres.
COMMUNITY_SHUTTLE_KM = 10_920_849.0
CONTRACT_COMMUNITY_SHUTTLE_KM = 2_732_670.0

# ---------------------------------------------------------------------------
# Statistics Canada Table 36-10-0595-01, 2022, British Columbia, within-province
# multipliers.  Values are as published from the CSV (not rounded in formulas).
# ---------------------------------------------------------------------------

IO_SECTOR_PROXY = {
    "industry": "Other transit and ground passenger transportation and scenic and sightseeing transportation [BS48A000]",
    "gdp_direct_per_output": 0.619,
    "gdp_simple_per_output": 0.806,
    "gdp_total_per_output": 1.097,
    "jobs_direct_per_million": 4.891,
    "jobs_simple_per_million": 6.174,
    "jobs_total_per_million": 8.027,
    "labour_income_direct_per_output": 0.429,
    "labour_income_simple_per_output": 0.509,
    "labour_income_total_per_output": 0.595,
}

ENGINEERING_CONSTRUCTION = {
    "industry": "Other engineering construction [BS23C500]",
    "gdp_direct_per_output": 0.363,
    "gdp_simple_per_output": 0.614,
    "gdp_total_per_output": 0.817,
    "jobs_direct_per_million": 2.443,
    "jobs_simple_per_million": 4.203,
    "jobs_total_per_million": 5.494,
    "labour_income_direct_per_output": 0.231,
    "labour_income_simple_per_output": 0.387,
    "labour_income_total_per_output": 0.457,
}

BUS_BODY_MANUFACTURING = {
    "industry": "Motor vehicle body and trailer manufacturing [BS336200]",
    "gdp_direct_per_output": 0.352,
    "gdp_simple_per_output": 0.457,
    "gdp_total_per_output": 0.611,
    "jobs_direct_per_million": 3.555,
    "jobs_simple_per_million": 4.323,
    "jobs_total_per_million": 5.300,
}

# Urban transit systems BS485100 is documented as a rejected base row: its
# direct labour-income coefficient exceeds its output coefficient and its GDP
# coefficients become negative in several provinces.  This is consistent with
# public-transit transfer accounting and makes it unsafe for a benefit claim.
URBAN_TRANSIT_RAW_BC_2022 = {
    "gdp_direct_per_output": 0.098,
    "gdp_simple_per_output": 0.503,
    "gdp_total_per_output": 1.260,
    "jobs_direct_per_million": 14.057,
    "jobs_simple_per_million": 17.629,
    "jobs_total_per_million": 22.444,
    "labour_income_direct_per_output": 1.344,
    "wages_direct_per_output": 1.094,
}

# ---------------------------------------------------------------------------
# EEA/COPERT Appendix 4 coefficients for urban buses, 50% load, 0% slope.
# Coefficient vector order: alpha, beta, gamma, delta, epsilon, zeta, eta.
# A separate reduction factor is applied exactly as in the workbook equation.
# ---------------------------------------------------------------------------

EEA_DIESEL_URBAN_15_18_EURO_VI = {
    "NOx": ([181.6450509528872, 11196.70591002358, -86923.50339496524,
             -178082.241348017, 268.4244141309995, 5622.852151466637,
             -67105.02513131434], 0.0),
    "PM Exhaust (urban)": ([-0.000313881923547988, -0.0145484315009182,
                            5.33927720306299, 4.32988739703353,
                            -0.000119639044053958, 0.0102176505703206,
                            0.211097947587396], 0.999344299776013),
    "EC (MJ/km)": ([-7.289143631615881, 640.0828583578445,
                    13785.15089625432, -109902.1922219768,
                    -1.475481308546263, 135.6939022337642,
                    -837.4527868155939], 0.0),
}

EEA_CNG_URBAN_15_18_EURO_VI = {
    "NOx": ([1.454364, 12.28338, -3572.43, 81982.7, 16.63304,
             -871.796, 13263.24], 0.0),
    "PM Exhaust (urban)": ([0.00668361463754694, -0.905301305406419,
                            43.27101279318, 0.0, 0.0, 0.0,
                            3829.84944299177], 0.0),
    "EC (MJ/km)": ([2.902952, -7.92778, -948.88, 8227.055,
                    0.309673, -7.13133, 43.29193], 0.0),
}


def copert_factor(coefficients: list[float], speed_kmh: float,
                  reduction_fraction: float = 0.0) -> float:
    """Evaluate the EMEP/EEA hot-emission equation in g/km or MJ/km."""
    a, b, c, d, e, z, h = coefficients
    speed = float(speed_kmh)
    numerator = a * speed**2 + b * speed + c + d / speed
    denominator = e * speed**2 + z * speed + h
    value = numerator / denominator * (1.0 - reduction_fraction)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid COPERT result {value} at {speed} km/h")
    return value


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def get_fleet_metric(rows: list[dict[str, str]], snapshot: str, metric: str) -> float:
    matches = [float(row["value"]) for row in rows
               if row["snapshot"] == snapshot and row["metric"] == metric]
    if len(matches) != 1:
        raise ValueError(f"Expected one {snapshot}/{metric} row, got {matches}")
    return matches[0]


def economic_bounds(scenario_data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build annual operations, transitional infrastructure, and a memo ceiling."""
    local_envelope = BUS_WAGES_CAD_M + BC_SUPPLIER_SPEND_SHARE * (
        BUS_OPERATIONS_CAD_M - BUS_WAGES_CAD_M
    )
    retained_supplier_spend = BC_SUPPLIER_SPEND_SHARE * (
        BUS_OPERATIONS_CAD_M - BUS_WAGES_CAD_M
    )
    direct_fte = BUS_WAGES_CAD_M / (AVERAGE_ANNUAL_COMPENSATION_CAD / 1_000_000.0)

    ratios = {
        "gdp_simple": IO_SECTOR_PROXY["gdp_simple_per_output"] / IO_SECTOR_PROXY["gdp_direct_per_output"],
        "gdp_total": IO_SECTOR_PROXY["gdp_total_per_output"] / IO_SECTOR_PROXY["gdp_direct_per_output"],
        "jobs_simple": IO_SECTOR_PROXY["jobs_simple_per_million"] / IO_SECTOR_PROXY["jobs_direct_per_million"],
        "jobs_total": IO_SECTOR_PROXY["jobs_total_per_million"] / IO_SECTOR_PROXY["jobs_direct_per_million"],
        "wage_simple": IO_SECTOR_PROXY["labour_income_simple_per_output"] / IO_SECTOR_PROXY["labour_income_direct_per_output"],
        "wage_total": IO_SECTOR_PROXY["labour_income_total_per_output"] / IO_SECTOR_PROXY["labour_income_direct_per_output"],
    }

    def apply_ratio(direct: float, ratio: float) -> float:
        # q is applied only to the spillover above the measured direct base.
        return direct * (1.0 + BC_SUPPLIER_SPEND_SHARE * (ratio - 1.0))

    operations = [
        {
            "scenario": "low",
            "component": "bus_operations_recurring",
            "recurrence": "annual_2023",
            "reported_spend_m_cad": BUS_OPERATIONS_CAD_M,
            "regional_spend_envelope_m_cad": local_envelope,
            "bc_supplier_retained_spend_m_cad": retained_supplier_spend,
            "regional_value_added_proxy_m_cad": BUS_WAGES_CAD_M,
            "wage_income_m_cad": BUS_WAGES_CAD_M,
            "direct_fte": direct_fte,
            "total_fte": direct_fte,
            "accounting_rule": "measured direct payroll floor; not total GDP",
            "source_basis": "TransLink 2025 Business Plan p.21; Transport Canada RO13 2023P",
            "additive_to_capital": False,
            "status": "LOW_DIRECT_FLOOR",
        },
        {
            "scenario": "central",
            "component": "bus_operations_recurring",
            "recurrence": "annual_2023",
            "reported_spend_m_cad": BUS_OPERATIONS_CAD_M,
            "regional_spend_envelope_m_cad": local_envelope,
            "bc_supplier_retained_spend_m_cad": retained_supplier_spend,
            "regional_value_added_proxy_m_cad": apply_ratio(BUS_WAGES_CAD_M, ratios["gdp_simple"]),
            "wage_income_m_cad": apply_ratio(BUS_WAGES_CAD_M, ratios["wage_simple"]),
            "direct_fte": direct_fte,
            "total_fte": apply_ratio(direct_fte, ratios["jobs_simple"]),
            "accounting_rule": "direct+indirect; 72.5% BC supplier retention on spillovers",
            "source_basis": "TransLink 2025 Business Plan p.21; TransLink 2023 Accountability p.63; StatCan 36-10-0595-01 BS48A000; RO13",
            "additive_to_capital": False,
            "status": "CENTRAL_SECTOR_PROXY",
        },
        {
            "scenario": "high",
            "component": "bus_operations_recurring",
            "recurrence": "annual_2023",
            "reported_spend_m_cad": BUS_OPERATIONS_CAD_M,
            "regional_spend_envelope_m_cad": local_envelope,
            "bc_supplier_retained_spend_m_cad": retained_supplier_spend,
            "regional_value_added_proxy_m_cad": apply_ratio(BUS_WAGES_CAD_M, ratios["gdp_total"]),
            "wage_income_m_cad": apply_ratio(BUS_WAGES_CAD_M, ratios["wage_total"]),
            "direct_fte": direct_fte,
            "total_fte": apply_ratio(direct_fte, ratios["jobs_total"]),
            "accounting_rule": "direct+indirect+induced; 72.5% BC supplier retention on spillovers",
            "source_basis": "TransLink 2025 Business Plan p.21; TransLink 2023 Accountability p.63; StatCan 36-10-0595-01 BS48A000; RO13",
            "additive_to_capital": False,
            "status": "HIGH_SECTOR_PROXY_NOT_NET_BENEFIT",
        },
    ]

    # The project's saved transition cases supply infrastructure and bus-purchase
    # envelopes.  Only infrastructure is used in the core regional calculation;
    # vehicle manufacturing is a separate, non-additive upper ceiling because the
    # available evidence does not show that bus final assembly occurs in BC.
    econ_cases = {case["case"]: case for case in scenario_data["economics"]}
    infra_spend = {name: econ_cases[name]["infrastructure_gross_cad"] / 1_000_000
                   for name in ("low", "central", "high")}
    bus_spend = {name: econ_cases[name]["plan_bus_capex_cad"] / 1_000_000
                 for name in ("low", "central", "high")}

    infra_rows: list[dict[str, Any]] = []
    ceiling_rows: list[dict[str, Any]] = []
    for name, multiplier_profile in (
        ("low", "direct"),
        ("central", "simple"),
        ("high", "total"),
    ):
        spend = infra_spend[name]
        if multiplier_profile == "direct":
            gdp = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["gdp_direct_per_output"]
            wage = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["labour_income_direct_per_output"]
            jobs = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["jobs_direct_per_million"]
        elif multiplier_profile == "simple":
            gdp = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["gdp_simple_per_output"]
            wage = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["labour_income_simple_per_output"]
            jobs = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["jobs_simple_per_million"]
        else:
            gdp = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["gdp_total_per_output"]
            wage = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["labour_income_total_per_output"]
            jobs = spend * BC_SUPPLIER_SPEND_SHARE * ENGINEERING_CONSTRUCTION["jobs_total_per_million"]

        infra_rows.append({
            "scenario": name,
            "component": "zeb_infrastructure_transitional",
            "recurrence": "one_time_2024_2031",
            "reported_spend_m_cad": spend,
            "regional_spend_envelope_m_cad": spend * BC_SUPPLIER_SPEND_SHARE,
            "bc_supplier_retained_spend_m_cad": spend * BC_SUPPLIER_SPEND_SHARE,
            "regional_value_added_proxy_m_cad": gdp,
            "wage_income_m_cad": wage,
            "direct_fte": None,
            "total_fte": None,
            "job_years": jobs,
            "annual_average_gva_m_cad": gdp / 8.0,
            "annual_average_fte": jobs / 8.0,
            "accounting_rule": "gross transitional value-added, not a net benefit; no revenue or benefit recognition of capex",
            "source_basis": f"StatCan 36-10-0595-01 BS23C500; project infrastructure envelope ({multiplier_profile}); assumed 2024--2031 phase",
            "additive_to_capital": False,
            "status": "SEPARATE_ONE_TIME_MEMO",
        })

        bus = bus_spend[name]
        if name == "low":
            gdp_c = bus * BC_SUPPLIER_SPEND_SHARE * BUS_BODY_MANUFACTURING["gdp_direct_per_output"]
            jobs_c = bus * BC_SUPPLIER_SPEND_SHARE * BUS_BODY_MANUFACTURING["jobs_direct_per_million"]
        elif name == "central":
            gdp_c = bus * BC_SUPPLIER_SPEND_SHARE * BUS_BODY_MANUFACTURING["gdp_simple_per_output"]
            jobs_c = bus * BC_SUPPLIER_SPEND_SHARE * BUS_BODY_MANUFACTURING["jobs_simple_per_million"]
        else:
            gdp_c = bus * BC_SUPPLIER_SPEND_SHARE * BUS_BODY_MANUFACTURING["gdp_total_per_output"]
            jobs_c = bus * BC_SUPPLIER_SPEND_SHARE * BUS_BODY_MANUFACTURING["jobs_total_per_million"]
        ceiling_rows.append({
            "scenario": name,
            "component": "bus_manufacturing_ceiling_not_included",
            "recurrence": "one_time_2024_2033",
            "reported_spend_m_cad": bus,
            "regional_spend_envelope_m_cad": bus * BC_SUPPLIER_SPEND_SHARE,
            "bc_supplier_retained_spend_m_cad": bus * BC_SUPPLIER_SPEND_SHARE,
            "regional_value_added_proxy_m_cad": gdp_c,
            "wage_income_m_cad": None,
            "direct_fte": None,
            "total_fte": None,
            "job_years": jobs_c,
            "accounting_rule": "NON-ADDITIVE ceiling assuming 72.5% BC manufacturing content; final-assembly location unverified",
            "source_basis": f"StatCan 36-10-0595-01 BS336200; project bus-purchase envelope ({multiplier_profile})",
            "additive_to_capital": False,
            "status": "EXCLUDED_FROM_CORE",
        })

    detail = {
        "local_operating_envelope_m_cad": local_envelope,
        "bc_supplier_retained_operating_spend_m_cad": retained_supplier_spend,
        "direct_fte_from_payroll": direct_fte,
        "multiplier_ratios": ratios,
        "reported_bus_operations_m_cad": BUS_OPERATIONS_CAD_M,
        "reported_wages_m_cad": BUS_WAGES_CAD_M,
        "bc_supplier_spend_share": BC_SUPPLIER_SPEND_SHARE,
        "infrastructure_spend_m_cad": infra_spend,
        "bus_purchase_spend_m_cad": bus_spend,
        "operations_formula": "D=W/C; G_L=W; G_s=W*(1+q*(bG_s-1)); G_t=W*(1+q*(bG_t-1)); J_s=D*(1+q*(bJ_s-1)); J_t=D*(1+q*(bJ_t-1))",
        "capital_formula": "G_c,i=q*I_i*m_GDP,i; JobYears_c,i=q*I_i,million*m_jobs,i; annual average assumes eight-year infrastructure phase",
        "do_not_add": "Operations are recurring. Infrastructure and vehicle rows are one-time gross activity envelopes and are never added to annual operations as returns or benefits.",
        "capex_is_not_revenue": True,
        "vehicle_manufacturing_in_core": False,
    }
    portfolio_rows = operations + infra_rows + ceiling_rows
    for row in portfolio_rows:
        row["region"] = "Metro Vancouver / British Columbia"
        if row["component"] == "bus_operations_recurring":
            row["scope"] = "TransLink published Bus Operations umbrella; includes SeaBus and Access Transit"
        elif row["component"] == "zeb_infrastructure_transitional":
            row["scope"] = "conditional 2024--2031 zero-emission bus infrastructure envelope"
        else:
            row["scope"] = "conditional bus-purchase envelope; BC manufacturing content unverified"
    return portfolio_rows, detail


def activity_split(scenario_data: dict[str, Any], block_audit: dict[str, Any]) -> dict[str, Any]:
    weekday = next(day for day in block_audit["days"] if day["kind"] == "weekday")
    classes = weekday["classes"]
    trolley_lower = classes["cap47"]["distance_lower_km"] + classes["cap70"]["distance_lower_km"]
    trolley_upper = classes["cap47"]["distance_upper_km"] + classes["cap70"]["distance_upper_km"]
    total_lower = weekday["distance_lower_km"]
    total_upper = weekday["distance_upper_km"]

    fossil_share_low = 1.0 - trolley_lower / total_lower
    fossil_share_high = 1.0 - trolley_upper / total_upper
    fossil_share_central = 0.5 * (fossil_share_low + fossil_share_high)

    total_ng_gj = RNG_GJ_2023 / RNG_SHARE_OF_NATURAL_GAS
    speed = BUS_SERVICE_KM / BUS_SERVICE_HOURS
    cng_ec_mj_km = copert_factor(EEA_CNG_URBAN_15_18_EURO_VI["EC (MJ/km)"][0], speed)
    cng_km = total_ng_gj * 1000.0 / cng_ec_mj_km
    gas_km = COMMUNITY_SHUTTLE_KM + CONTRACT_COMMUNITY_SHUTTLE_KM
    diesel_share = DIESEL_BUS_COUNT / (DIESEL_BUS_COUNT + HYBRID_BUS_COUNT)

    activity = {
        "speed_kmh": speed,
        "total_bus_service_km": BUS_SERVICE_KM,
        "community_and_contract_shuttle_km": gas_km,
        "total_purchased_natural_gas_gj": total_ng_gj,
        "cng_energy_mj_per_km": cng_ec_mj_km,
        "cng_km_inferred": cng_km,
        "fossil_share_low": fossil_share_low,
        "fossil_share_central": fossil_share_central,
        "fossil_share_high": fossil_share_high,
        "diesel_stock": DIESEL_BUS_COUNT,
        "hybrid_stock": HYBRID_BUS_COUNT,
        "diesel_share_of_remaining_fossil_vkt_proxy": diesel_share,
        "existing_scenario_fossil_km_crosscheck": scenario_data["service_baseline"]["annual_nondeck_fossil_km_estimate"],
        "quality": "PROXY_FIXED_SERVICE_FUEL_ALLOCATION",
        "warning": "The 2022 stock split is not a 2023 vehicle-km register. Community shuttles are assigned to gasoline and the remaining diesel/hybrid activity is stock-weighted.",
    }
    return activity


def aq_factor_sets(speed_kmh: float) -> dict[str, dict[str, dict[str, float]]]:
    diesel_nox = copert_factor(EEA_DIESEL_URBAN_15_18_EURO_VI["NOx"][0], speed_kmh)
    diesel_pm_coeff, diesel_pm_rf = EEA_DIESEL_URBAN_15_18_EURO_VI["PM Exhaust (urban)"]
    diesel_pm = copert_factor(diesel_pm_coeff, speed_kmh, diesel_pm_rf)
    cng_nox = copert_factor(EEA_CNG_URBAN_15_18_EURO_VI["NOx"][0], speed_kmh)
    cng_pm_coeff, cng_pm_rf = EEA_CNG_URBAN_15_18_EURO_VI["PM Exhaust (urban)"]
    cng_pm = copert_factor(cng_pm_coeff, speed_kmh, cng_pm_rf)

    # BC Vanderhoof inventory, Table 4, uses g/VKT for generic on-road buses
    # from older LVFEI/Alberni inputs.  It is retained only as an upper end.
    bc_gas = {"NOx": 2.98, "PM2.5": 0.03, "PM10": 0.12}
    bc_diesel = {"NOx": 6.79, "PM2.5": 0.15, "PM10": 0.24}

    low = {
        "diesel": {"NOx": diesel_nox, "PM2.5": diesel_pm, "PM10": diesel_pm},
        "hybrid": {"NOx": diesel_nox, "PM2.5": diesel_pm, "PM10": diesel_pm},
        "cng": {"NOx": cng_nox, "PM2.5": cng_pm, "PM10": cng_pm},
        "gasoline_shuttle": dict(bc_gas),
    }
    central = {
        # Real-world Euro VI Paris values/approximate low-speed results: the
        # cited article reports about 2.0 diesel, 1.4 hybrid and 0.6 CNG g/km.
        "diesel": {"NOx": 2.0, "PM2.5": 0.5 * (diesel_pm + bc_diesel["PM2.5"]),
                    "PM10": 0.5 * (diesel_pm + bc_diesel["PM10"])},
        "hybrid": {"NOx": 1.4, "PM2.5": 0.5 * (diesel_pm + bc_diesel["PM2.5"]),
                    "PM10": 0.5 * (diesel_pm + bc_diesel["PM10"])},
        "cng": {"NOx": 0.6, "PM2.5": cng_pm, "PM10": cng_pm},
        "gasoline_shuttle": dict(bc_gas),
    }
    high = {
        "diesel": {k: bc_diesel[k] for k in ("NOx", "PM2.5", "PM10")},
        "hybrid": {k: bc_diesel[k] for k in ("NOx", "PM2.5", "PM10")},
        # No official BC CNG bus factor was located. Preserve the measured
        # low-speed CNG value instead of silently assigning diesel PM to CNG.
        "cng": {"NOx": 0.6, "PM2.5": cng_pm, "PM10": cng_pm},
        "gasoline_shuttle": dict(bc_gas),
    }
    return {"low": low, "central": central, "high": high}


def air_quality_bounds(activity: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    factors = aq_factor_sets(activity["speed_kmh"])
    scenario_shares = {
        "low": activity["fossil_share_low"],
        "central": activity["fossil_share_central"],
        "high": activity["fossil_share_high"],
    }
    gas_km = activity["community_and_contract_shuttle_km"]
    cng_km = activity["cng_km_inferred"]
    diesel_share = activity["diesel_share_of_remaining_fossil_vkt_proxy"]
    summary: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []

    for name in ("low", "central", "high"):
        fossil_km = BUS_SERVICE_KM * scenario_shares[name]
        residual_km = fossil_km - gas_km - cng_km
        if residual_km <= 0:
            raise ValueError("Fuel split consumes more than total fossil service km")
        diesel_km = residual_km * diesel_share
        hybrid_km = residual_km - diesel_km
        fuel_km = {
            "diesel": diesel_km,
            "hybrid": hybrid_km,
            "cng": cng_km,
            "gasoline_shuttle": gas_km,
        }
        pollutant_mass = {pollutant: 0.0 for pollutant in ("NOx", "PM2.5", "PM10")}
        for fuel, km in fuel_km.items():
            for pollutant in pollutant_mass:
                ef = factors[name][fuel][pollutant]
                grams = km * ef
                pollutant_mass[pollutant] += grams
                if fuel == "gasoline_shuttle":
                    source = "BC Ministry of Environment and Climate Change Strategy, Vanderhoof inventory"
                    locator = "Table 4, Gasoline Bus"
                    derivation = "legacy on-road bus factor, g/VKT"
                elif name == "low":
                    source = "EEA/EMEP Guidebook 2023, Road Transport Appendix 4"
                    locator = "HOT_EMISSIONS_PARAMETERS; Euro VI D/E; 50% load; 0% slope"
                    derivation = "COPERT equation at 19.1666 km/h"
                elif fuel in ("diesel", "hybrid") and name == "central":
                    if pollutant == "NOx":
                        source = "Prati et al., Atmosphere 16(3), 293 (2025)"
                        locator = "abstract/results, low-speed real-world NOx"
                        derivation = "reported approximate low-speed value"
                    else:
                        source = "Derived from EEA Appendix 4 and BC Vanderhoof Table 4"
                        locator = "arithmetic midpoint"
                        derivation = "central PM sensitivity, not a measured value"
                elif fuel == "cng" and name == "central" and pollutant == "NOx":
                    source = "Prati et al., Atmosphere 16(3), 293 (2025)"
                    locator = "abstract/results, low-speed real-world NOx"
                    derivation = "reported approximate low-speed value"
                elif fuel == "cng" and name == "central":
                    source = "EEA/EMEP Guidebook 2023, Road Transport Appendix 4"
                    locator = "HOT_EMISSIONS_PARAMETERS; CNG Euro VI D/E; urban PM"
                    derivation = "COPERT exhaust PM; PM2.5=PM10=TSP in source"
                elif fuel in ("diesel", "hybrid") and name == "high":
                    source = "BC Ministry of Environment and Climate Change Strategy, Vanderhoof inventory"
                    locator = "Table 4, Diesel Bus"
                    derivation = "legacy on-road bus factor, g/VKT; conservative upper end"
                elif fuel == "cng" and name == "high" and pollutant == "NOx":
                    source = "Prati et al., Atmosphere 16(3), 293 (2025)"
                    locator = "abstract/results, low-speed real-world NOx"
                    derivation = "no BC-specific CNG factor located"
                elif fuel == "cng" and name == "high":
                    source = "EEA/EMEP Guidebook 2023, Road Transport Appendix 4"
                    locator = "HOT_EMISSIONS_PARAMETERS; CNG Euro VI D/E; urban PM"
                    derivation = "no BC-specific CNG PM factor located"
                else:
                    source = "EEA/EMEP Guidebook 2023, Road Transport Appendix 4"
                    locator = "HOT_EMISSIONS_PARAMETERS"
                    derivation = "source factor"
                factor_rows.append({
                    "scenario": name,
                    "fuel": fuel,
                    "pollutant": pollutant,
                    "g_per_km": ef,
                    "activity_km": km,
                    "mass_tonnes": grams / 1_000_000.0,
                    "source": source,
                    "source_locator": locator,
                    "derivation": derivation,
                })

        summary.append({
            "scenario": name,
            "speed_kmh": activity["speed_kmh"],
            "fossil_service_share": scenario_shares[name],
            "total_fossil_km": fossil_km,
            "fuel_km": fuel_km,
            "pollutant_tonnes": {k: v / 1_000_000.0 for k, v in pollutant_mass.items()},
            "fleet_average_g_per_km": {k: v / BUS_SERVICE_KM for k, v in pollutant_mass.items()},
            "scope": "fixed-route bus tailpipe exhaust; SeaBus, HandyDART, rail and non-revenue vehicles excluded",
            "status": "BUS_ONLY_PROXY_WITH_ACTIVITY_ALLOCATION",
        })

    detail = {
        "factor_sets": factors,
        "activity": activity,
        "factor_rows": factor_rows,
        "boundary": {
            "bus_only": True,
            "tailpipe_exhaust_only": True,
            "brake_and_tire_wear_included": False,
            "fuel_upstream_included": False,
            "electricity_upstream_included": False,
            "all_revenue_fleet_cac_series_used": False,
        },
        "warnings": [
            "Emission factors are not a 2023 Vancouver chassis/PEMS certification.",
            "CNG service km is inferred from purchased-gas energy and an EEA energy-consumption factor.",
            "The gasoline-shuttle factor is the BC legacy inventory bus factor; no newer BC bus factor was located.",
            "The high PM and NOx diesel/hybrid values are a conservative legacy-fleet envelope from the BC inventory, not a claim about every 2023 bus.",
            "PM exhaust is treated as having PM2.5 = PM10 = TSP in the EEA workbook; the BC legacy rows retain separate PM2.5 and PM10 columns.",
            "The existing transition scenario's 88.79 million non-deck fossil-km estimate excludes double-deck blocks and is a cross-check, not this audit's total activity denominator.",
            "The five or so 2023 in-service battery-electric buses are not separately observable in the service-km feed; treating all non-trolley activity as fossil is a small conservative bias.",
        ],
    }
    return summary, detail


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    actual_service = read_csv_rows(ROOT / "data/processed/translink_2023_actual_service.csv")
    fixed_service = sum(float(row["service_km"]) for row in actual_service
                        if row["service_group"] != "seabus")
    if abs(fixed_service - BUS_SERVICE_KM) > 1e-3:
        raise ValueError(f"Fixed-route service-km mismatch: {fixed_service}")

    fleet_rows = read_csv_rows(ROOT / "data/processed/translink_fleet_bridge_2023_2025.csv")
    if int(get_fleet_metric(fleet_rows, "2022", "low_emission_diesel")) != DIESEL_BUS_COUNT:
        raise ValueError("Diesel stock changed in project data")
    if int(get_fleet_metric(fleet_rows, "2022", "cng")) != CNG_BUS_COUNT:
        raise ValueError("CNG stock changed in project data")

    scenario_data = json.loads(
        (ROOT / "results/vancouver_transition_scenarios.json").read_text(encoding="utf-8")
    )
    block_audit = json.loads(
        (ROOT / "results/vancouver_block_range_audit.json").read_text(encoding="utf-8")
    )

    economic_rows, economic_detail = economic_bounds(scenario_data)
    activity = activity_split(scenario_data, block_audit)
    air_rows, air_detail = air_quality_bounds(activity)

    regional_csv = ROOT / "data/processed/regional_economic_bounds_2023.csv"
    write_csv(
        regional_csv,
        economic_rows,
        [
            "scenario", "region", "component", "scope", "recurrence", "reported_spend_m_cad",
            "bc_supplier_retained_spend_m_cad", "regional_spend_envelope_m_cad",
            "regional_value_added_proxy_m_cad",
            "wage_income_m_cad", "direct_fte", "total_fte", "job_years",
            "annual_average_gva_m_cad", "annual_average_fte",
            "accounting_rule", "source_basis", "additive_to_capital", "status",
        ],
    )

    air_csv = ROOT / "data/processed/transit_air_quality_factors_2023.csv"
    write_csv(
        air_csv,
        air_detail["factor_rows"],
        ["scenario", "fuel", "pollutant", "g_per_km", "activity_km", "mass_tonnes",
         "source", "source_locator", "derivation"],
    )

    regional_json = ROOT / "data/processed/regional_economic_bounds_2023.json"
    regional_json.write_text(json.dumps({
        "status": "EXECUTED_SOURCE_BOUNDS_SEPARATE_ACCOUNTS",
        "detail": economic_detail,
        "rows": economic_rows,
        "sources": [
            "TransLink (2025 Business Plan), p. 21, 2023 actual Bus Operations by Category",
            "TransLink (2023 Accountability Report), PDF p. 63, 72.5% BC supplier share of total spend",
            "Statistics Canada Table 36-10-0595-01, 2022, British Columbia within-province multipliers, DOI 10.25318/3610059501-eng",
            "Transport Canada Table RO13 (2024), 2023P urban-transit average annual compensation CAD 102,872; Statistics Canada Table 23-10-0083-01",
            "Project transition scenario: results/vancouver_transition_scenarios.json",
        ],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    air_json = ROOT / "data/processed/transit_air_quality_factors_2023.json"
    air_json.write_text(json.dumps({
        "status": "EXECUTED_SOURCE_AUDIT_FUEL_ALLOCATION_PROXY",
        "detail": air_detail,
        "scenarios": air_rows,
        "sources": [
            "TransLink 2025 Business Plan, pp. 21 and 23 (2023 service km and fuel-energy context)",
            "TransLink 2023 Accountability Report, pp. 38 and 63 (RNG energy and BC procurement share)",
            "EEA/EMEP Guidebook 2023, Road Transport Appendix 4, July 2026 workbook, urban bus Euro VI D/E coefficients",
            "MDPI Atmosphere 16(3), 293 (2025), real-world Euro VI diesel/hybrid/CNG urban bus low-speed results",
            "BC Ministry of Environment and Climate Change Strategy, Vanderhoof emission inventory, Table 4",
        ],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    audit = {
        "status": "EXECUTED_SOURCE_AUDIT_WITH_UNRESOLVED_FLEET_FUEL_ALLOCATION",
        "economic": {
            "rows": economic_rows,
            "detail": economic_detail,
            "score_use": "Do not add capital to recurring operations; capital is gross transitional activity, not net benefit.",
        },
        "air_quality": {
            "scenarios": air_rows,
            "detail": air_detail,
            "bus_service_km": BUS_SERVICE_KM,
            "service_hours": BUS_SERVICE_HOURS,
            "average_operating_speed_kmh": BUS_SERVICE_KM / BUS_SERVICE_HOURS,
        },
        "excluded": {
            "all_revenue_fleet_cac_series": "Excluded because it cannot be split into fixed-route bus modes or pollutants.",
            "handydart_seabus_rail": "Excluded from all air-quality totals.",
            "depot_and_vehicle_manufacturing": "Excluded from bus tailpipe totals; treated separately in economic memo only.",
        },
        "sources": [
            {"name": "TransLink 2025 Business Plan", "locator": "p. 21 (2023 Bus Operations actual), p. 23 (2023 service kilometres)", "url": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/business_plan/2025-business-plan-operating-and-capital-budget-summary.pdf"},
            {"name": "TransLink 2023 Accountability Report", "locator": "PDF p. 38 (RNG and CNG count), PDF p. 63 (72.5% BC supplier spend)", "url": "https://www.translink.ca/-/media/translink/documents/about-translink/corporate-reports/accountability_reports/2023/accountability_report_2023.pdf"},
            {"name": "Statistics Canada input-output multipliers", "locator": "Table 36-10-0595-01, 2022, British Columbia, within province, rows BS48A000/BS23C500/BS336200", "url": "https://doi.org/10.25318/3610059501-eng"},
            {"name": "Transport Canada Table RO13", "locator": "2014--2023, urban transit systems, 2023P", "url": "https://tdih-cdit.tc.canada.ca/en/addendum-tables/2024/table-ro13-average-annual-compensation-bus-industry-2014-2023-0"},
            {"name": "EEA/EMEP Guidebook 2023", "locator": "Road Transport Appendix 4, July 2026 workbook, urban Euro VI D/E bus rows", "url": "https://www.eea.europa.eu/en/analysis/publications/emep-eea-guidebook-2023/part-b-sectoral-guidance-chapters/1-energy/1-a-combustion/1-a-3-b-i-1"},
            {"name": "Prati et al. (2025)", "locator": "Atmosphere 16(3), 293, real-world low-speed NOx", "url": "https://doi.org/10.3390/atmos16030293"},
            {"name": "BC Vanderhoof emissions inventory", "locator": "Table 4, Diesel Bus and Gasoline Bus on-road factors", "url": "https://www2.gov.bc.ca/gov/content/environment/air-land-water/air/reports/emission-inventory-vanderhoof"},
        ],
        "checks": {
            "fixed_route_service_km_reconciles": True,
            "fleet_counts_match_processed_snapshot": True,
            "air_quality_activity_reconciles_to_fossil_proxy": True,
            "gross_capex_not_added_to_benefits": True,
        },
        "limitations": [
            "No observed 2023 vehicle-km split by powertrain/fuel was available.",
            "The economic operation envelope is TransLink's published Bus Operations umbrella and includes SeaBus and Access Transit.",
            "The economic results are BC-level sector proxies rather than a Metro Vancouver GDP account.",
            "The Statistics Canada IO result is a sector proxy, not a TransLink-specific multiplier.",
            "The construction envelope is from a conditional transition scenario and must not be called committed spending.",
            "The BC legacy emission factors are not a direct 2023 bus certification.",
        ],
        "outputs": [str(regional_csv.relative_to(ROOT)), str(regional_json.relative_to(ROOT)),
                    str(air_csv.relative_to(ROOT)), str(air_json.relative_to(ROOT))],
    }
    audit_path = ROOT / "results/regional_and_air_quality_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "economic": economic_rows,
        "air_quality": air_rows,
        "outputs": audit["outputs"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
