import json
import csv
from pathlib import Path

from src.build_threecity_execution_v3 import (CTA_FMP_ARTICULATED,
                                              CTA_FMP_STANDARD,
                                              load_cta_age_cohorts,
                                              solve_cta_conversion_schedule)


ROOT = Path(__file__).resolve().parents[1]


def test_cta_official_purchase_envelope_is_below_2033_conversion_need():
    result = json.loads((ROOT / "results/threecity_execution_certificates_v3.json").read_text())
    cert = result["chicago"]
    assert CTA_FMP_STANDARD == 1157
    assert CTA_FMP_ARTICULATED == 310
    short = cert["2033_electrification_shortfall_under_fmp"]
    assert short["standard_purchase_shortfall"] == 396
    assert short["total_purchase_shortfall"] == 385
    assert short["total_minimum_purchases"] == 1852


def test_cta_2024_ramp_remains_short_after_funded_life_extension():
    result = json.loads((ROOT / "results/threecity_execution_certificates_v3.json").read_text())
    ramp = result["chicago"]["2024_ramp_certificate"]
    assert ramp["due_at_14_year_cap_no_extension"] == 1056
    assert ramp["due_after_430_funded_life_extensions"] == 626
    assert ramp["due_after_608_fmp_max_life_extensions"] == 448
    assert ramp["shortfall_after_430_vs_200_budgeted_deliveries"] == 426
    assert ramp["entire_2023_26_purchase_envelope_vs_2024_due_after_430"] == -29


def test_cta_minimum_schedules_are_integer_and_deadline_compliant():
    cohorts = load_cta_age_cohorts()
    expected_peaks = {12: 1086, 14: 1056, 17: 539}
    for life, peak in expected_peaks.items():
        result = solve_cta_conversion_schedule(cohorts, life)
        assert result["minimum_peak_annual_purchases"] == peak
        rows = result["schedule"]
        assert sum(r["standard_non_electric_replacements"] for r in rows) == 1551
        assert sum(r["articulated_non_electric_replacements"] for r in rows) == 299
        std = art = 0
        for row in rows:
            std += row["standard_non_electric_replacements"]
            art += row["articulated_non_electric_replacements"]
            assert std >= sum(r["standard_due_slots"] for r in rows if r["year"] <= row["year"])
            assert art >= sum(r["articulated_due_slots"] for r in rows if r["year"] <= row["year"])
            assert all(isinstance(row[k], int) for k in ("standard_non_electric_replacements",
                                                         "articulated_non_electric_replacements"))
        assert rows[-1]["non_electric_slots_remaining"] == 0


def test_london_plan_preserves_body_counts_and_replaces_all_non_electric():
    result = json.loads((ROOT / "results/threecity_execution_certificates_v3.json").read_text())
    cert = result["london"]
    assert cert["fleet_basis"]["single_deck"] == 2445
    assert cert["fleet_basis"]["double_deck"] == 6198
    for scenario in cert["scenarios"]:
        rows = scenario["annual_plan"]
        assert sum(r["single_deck_non_electric_conversions"] for r in rows) == 2083
        assert sum(r["double_deck_non_electric_conversions"] for r in rows) == 5610
        assert rows[-1]["remaining_non_electric_total"] == 0
        assert rows[-1]["remaining_non_electric_single_deck"] == 0
        assert rows[-1]["remaining_non_electric_double_deck"] == 0
        assert sum(scenario["hydrogen_double_deck_converted_by_year"].values()) == 20
        assert scenario["strict_electric_body_class_certificate"] is True
        assert scenario["route_or_charging_certificate"] is False
        assert max(r["total_new_electric_deliveries"] for r in rows) <= scenario["minimum_peak_annual_new_electric_deliveries"]
        assert all(gap == 0 for gap in scenario["phase_mip_gaps"])


def test_london_peak_plan_matches_analytic_bound():
    result = json.loads((ROOT / "results/threecity_execution_certificates_v3.json").read_text())
    peaks = {s["life_cap_years"]: s["minimum_peak_annual_new_electric_deliveries"]
             for s in result["london"]["scenarios"]}
    assert peaks == {12: 2568, 14: 977, 17: 776}
    for scenario in result["london"]["scenarios"]:
        assert scenario["minimum_peak_annual_new_electric_deliveries"] == scenario["analytic_cumulative_deadline_bound"]


def test_procurement_batch_csv_conserves_units():
    rows = list(csv.DictReader((ROOT / "data/processed/threecity_execution_batches_v3.csv").open(encoding="utf-8")))
    london = [r for r in rows if r["city"] == "London" and r["life_cap_years"] == "17"]
    assert sum(int(r["units"]) for r in london if r["action"] == "non_electric_conversion") == 7693
    assert sum(int(r["units"]) for r in london if r["action"] == "existing_electric_renewal") == 66
    chicago = [r for r in rows if r["city"] == "Chicago" and r["life_cap_years"] == "14" and r["extension_units"] == "430"]
    assert sum(int(r["units"]) for r in chicago if r["action"] == "non_electric_conversion") == 1850
    assert sum(int(r["units"]) for r in chicago if r["action"] == "existing_electric_renewal") == 2
