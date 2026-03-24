from app.rules.base import ScheduleContext
from app.services.validator import validate_schedule, compute_score


SHIFT_TYPES = [
    {"id": 1, "name": "Mañana", "start_time": "07:00", "end_time": "14:30", "effective_hours": 7.5, "priority_order": 1},
    {"id": 2, "name": "Tarde", "start_time": "14:30", "end_time": "22:00", "effective_hours": 7.5, "priority_order": 2},
]

EMPLOYEES = [
    {"id": 1, "name": "Ana", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 2, "name": "Carlos", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
]


def _ctx(assignments, rules_config=None):
    return ScheduleContext(
        year=2026, month=3,
        employees=EMPLOYEES,
        shift_types=SHIFT_TYPES,
        absences=[],
        assignments=assignments,
        rules_config=rules_config or {},
    )


def test_validate_empty_schedule_reports_coverage_violations():
    violations = validate_schedule(_ctx([]))
    coverage_violations = [v for v in violations if v.rule_id == "min_daily_coverage"]
    assert len(coverage_violations) == 31


def test_validate_runs_multiple_rules():
    """Schedule with afternoon→morning (rest violation) and low coverage."""
    assignments = [
        {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
        {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 1},
    ]
    violations = validate_schedule(_ctx(assignments))

    rule_ids = {v.rule_id for v in violations}
    assert "min_rest_between_shifts" in rule_ids
    assert "min_daily_coverage" in rule_ids


def test_validate_skips_inactive_rules():
    from app.rules.registry import get_all_rules

    config = {rule.id: {"active": False} for rule in get_all_rules()}
    violations = validate_schedule(_ctx([], rules_config=config))
    assert len(violations) == 0


def test_compute_score_perfect():
    assert compute_score([]) == 100.0


def test_compute_score_with_structural_only():
    """Structural violations don't count."""
    from app.rules.base import Violation

    violations = [
        Violation("test", "2026-03-01", None, "grave", False, "structural"),
    ]
    assert compute_score(violations) == 100.0
