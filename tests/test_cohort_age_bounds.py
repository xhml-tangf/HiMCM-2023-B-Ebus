from src.audit_cta_2023 import age_due_bounds


def test_new_buses_are_not_treated_as_unknown_or_overdue():
    rows = [{"age_low": 0, "age_high": 0, "vehicles": 10},
            {"age_low": 13, "age_high": 15, "vehicles": 2},
            {"age_low": 16, "age_high": 20, "vehicles": 7}]
    assert age_due_bounds(rows, 15) == {
        "definitely_age_due_slots": 7,
        "possibly_age_due_slots": 9,
    }
