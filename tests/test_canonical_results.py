from pathlib import Path
import json
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_canonical_results import _annualized_lifecycle, _manufacture, build


def test_canonical_result_schema_and_sources():
    result = build()
    assert result["status"] == "CANONICAL_RESEARCH_RESULT"
    assert set(result) >= {"inputs", "schedule", "transition", "lifecycle_scores",
                           "city_comparison", "sensitivity", "verification"}
    assert len(result["city_comparison"]["cities"]) == 3
    assert result["inputs"]["baseline_fuel"] == "current low-carbon mix"
    assert result["verification"]["all_non_trolley_pattern_trips_preserved"] == 434_669
    assert result["verification"]["cyclic_collision"] == "PASS"


def test_manufacturing_boundary_is_separate_from_operating_score():
    # This is a small arithmetic check of the LCA leaves, not a dispatch test.
    assert _manufacture("standard", True) > _manufacture("standard", False)
    assert _manufacture("articulated", True) > _manufacture("standard", True)


def test_lifecycle_score_is_annualized_not_transition_sum():
    result = build()
    detail = result["lifecycle_scores"]["recommended_detail"]
    assert detail["basis"].startswith("annualized steady-state")
    assert detail["plan_total_t_year"] > 0
    assert detail["baseline_total_t_year"] > 0
    assert detail["environmental_score_pct"] == (
        100 * (detail["baseline_total_t_year"] - detail["plan_total_t_year"])
        / detail["baseline_total_t_year"]
    )
    assert detail["plan_total_t_year"] != result["transition"]["recommended"]["plan_ghg_t"]


def test_three_cities_have_explicit_boundary_and_no_fake_route_certificate():
    result = build()
    by_city = {row["city"]: row for row in result["city_comparison"]["cities"]}
    assert by_city["Vancouver"]["basis"] == "full-city scheduled plan"
    assert "case comparison" in by_city["Chicago"]["basis"]
    assert "case comparison" in by_city["London"]["basis"]
    assert by_city["London"]["annual_service_km"] is None
