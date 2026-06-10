from app.rules.base import ScheduleContext
from app.solver.solver import solve_schedule


SHIFT_TYPES = [
    {"id": 1, "name": "Mañana", "start_time": "07:00", "end_time": "14:30", "effective_hours": 7.5, "priority_order": 1},
    {"id": 2, "name": "Tarde", "start_time": "14:30", "end_time": "22:00", "effective_hours": 7.5, "priority_order": 2},
]

# 4 employees — enough to cover 2/day with rest days
EMPLOYEES = [
    {"id": 1, "name": "Ana", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 2, "name": "Carlos", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 3, "name": "María", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 4, "name": "Pedro", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
]

# Relaxed coverage for feasibility with small teams
RELAXED_CONFIG = {
    "min_daily_coverage": {"params": {"weekday_min": 1, "weekend_min": 1}},
}


def _ctx(employees=None, absences=None, rules_config=None, prev_assignments=None):
    return ScheduleContext(
        year=2026, month=3,
        employees=employees or EMPLOYEES,
        shift_types=SHIFT_TYPES,
        absences=absences or [],
        assignments=[],
        rules_config=rules_config or RELAXED_CONFIG,
        prev_assignments=prev_assignments or [],
    )


def test_solver_returns_optimal_or_feasible():
    result = solve_schedule(_ctx())
    assert result.status in ("optimal", "feasible")


def test_solver_assigns_shifts_to_all_employees():
    result = solve_schedule(_ctx())

    assert len(result.assignments) > 0
    emp_ids = {a["employee_id"] for a in result.assignments}
    for emp in EMPLOYEES:
        assert emp["id"] in emp_ids


def test_solver_one_shift_per_employee_per_day():
    result = solve_schedule(_ctx())

    from collections import Counter
    day_emp_counts = Counter(
        (a["date"], a["employee_id"])
        for a in result.assignments
        if a["shift_type_id"] is not None
    )
    assert all(count <= 1 for count in day_emp_counts.values())


def test_solver_no_rest_violations():
    result = solve_schedule(_ctx())

    rest_violations = [
        v for v in result.violations if v.rule_id == "min_rest_between_shifts"
    ]
    assert len(rest_violations) == 0


def test_solver_respects_absences():
    absences = [
        {"employee_id": 1, "start_date": "2026-03-01", "end_date": "2026-03-15", "type": "vacation"},
    ]
    result = solve_schedule(_ctx(absences=absences))

    ana_first_half = [
        a for a in result.assignments
        if a["employee_id"] == 1
        and a["date"] <= "2026-03-15"
        and a["shift_type_id"] is not None
    ]
    assert len(ana_first_half) == 0


def test_solver_performance():
    """4 employees × 31 days × 2 shifts should solve quickly."""
    result = solve_schedule(_ctx())
    assert result.solve_time_ms < 5000


def test_solver_infeasible_with_impossible_constraints():
    """2 employees, coverage=3 per day — impossible."""
    two_employees = EMPLOYEES[:2]
    config = {"min_daily_coverage": {"params": {"weekday_min": 3, "weekend_min": 3}}}
    result = solve_schedule(_ctx(employees=two_employees, rules_config=config))
    assert result.status == "infeasible"


def test_solver_respects_fixed_shift():
    fixed = [{"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2}]
    result = solve_schedule(_ctx(), fixed=fixed)

    assert result.status in ("optimal", "feasible")
    ana_mar2 = next(
        a for a in result.assignments
        if a["employee_id"] == 1 and a["date"] == "2026-03-02"
    )
    assert ana_mar2["shift_type_id"] == 2


def test_solver_respects_fixed_free_day():
    fixed = [{"date": "2026-03-10", "employee_id": 2, "shift_type_id": None}]
    result = solve_schedule(_ctx(), fixed=fixed)

    assert result.status in ("optimal", "feasible")
    carlos_mar10 = next(
        a for a in result.assignments
        if a["employee_id"] == 2 and a["date"] == "2026-03-10"
    )
    assert carlos_mar10["shift_type_id"] is None


def test_solver_avoids_rest_violation_with_prev_context():
    """If prev month ends with afternoon shift, solver should not assign morning on day 1."""
    prev = [
        {"date": "2026-02-28", "employee_id": 1, "shift_type_id": 2},
    ]
    result = solve_schedule(_ctx(prev_assignments=prev))

    assert result.status in ("optimal", "feasible")
    ana_mar1 = next(
        a for a in result.assignments
        if a["employee_id"] == 1 and a["date"] == "2026-03-01"
    )
    # Should NOT be morning (shift 1) because afternoon→morning = 9h rest < 12h min
    assert ana_mar1["shift_type_id"] != 1


def test_solver_prev_context_not_in_output():
    """Previous month dates should not appear in solver output."""
    prev = [
        {"date": "2026-02-28", "employee_id": 1, "shift_type_id": 2},
    ]
    result = solve_schedule(_ctx(prev_assignments=prev))

    output_dates = {a["date"] for a in result.assignments}
    assert "2026-02-28" not in output_dates
    assert all(d.startswith("2026-03") for d in output_dates)


def test_solver_distributes_work_days_fairly():
    """No employee should work significantly more or fewer days than others."""
    result = solve_schedule(_ctx())

    assert result.status in ("optimal", "feasible")
    days_per_emp = {}
    for a in result.assignments:
        if a["shift_type_id"] is not None:
            days_per_emp[a["employee_id"]] = days_per_emp.get(a["employee_id"], 0) + 1

    counts = list(days_per_emp.values())
    assert max(counts) - min(counts) <= 3


def test_solver_does_not_under_schedule():
    """With 4 employees and coverage=1, each should work at least 15 days in a 31-day month."""
    result = solve_schedule(_ctx())

    assert result.status in ("optimal", "feasible")
    days_per_emp = {}
    for a in result.assignments:
        if a["shift_type_id"] is not None:
            days_per_emp[a["employee_id"]] = days_per_emp.get(a["employee_id"], 0) + 1

    for emp_id, count in days_per_emp.items():
        assert count >= 15, f"Employee {emp_id} only works {count} days"


def test_solver_relaxes_desirable_rule_instead_of_failing():
    """2 employees + weekend coverage of 2 means nobody can have a free
    weekend; the desirable monthly_free_weekend rule must be relaxed
    instead of making the whole schedule infeasible."""
    config = {
        "min_daily_coverage": {"params": {"weekday_min": 1, "weekend_min": 2}},
    }
    result = solve_schedule(_ctx(employees=EMPLOYEES[:2], rules_config=config))

    assert result.status in ("optimal", "feasible")
    assert "monthly_free_weekend" in result.relaxed_rules

    free_weekend_violations = [
        v for v in result.violations if v.rule_id == "monthly_free_weekend"
    ]
    assert len(free_weekend_violations) == 2


def test_solver_relaxes_rule_demoted_to_desirable():
    """A mandatory rule demoted to desirable with an impossible minimum
    must produce a schedule instead of failing."""
    config = {
        "min_daily_coverage": {
            "priority": "desirable",
            "params": {"weekday_min": 10, "weekend_min": 10},
        },
    }
    result = solve_schedule(_ctx(rules_config=config))

    assert result.status in ("optimal", "feasible")
    assert "min_daily_coverage" in result.relaxed_rules


def test_solver_reports_no_relaxed_rules_when_all_satisfiable():
    result = solve_schedule(_ctx())

    assert result.status in ("optimal", "feasible")
    assert result.relaxed_rules == []


def test_solver_keeps_mandatory_rules_hard():
    """Mandatory rules must never be silently relaxed — an impossible
    mandatory rule still means infeasible."""
    config = {"min_daily_coverage": {"params": {"weekday_min": 10, "weekend_min": 10}}}
    result = solve_schedule(_ctx(rules_config=config))

    assert result.status == "infeasible"


def test_solver_max_weekly_hours_counts_prev_month_context():
    """Feb 23-27 2026 (Mon-Fri) at 7.5h/day exhausts Ana's 37.5h for the ISO
    week ending Sunday Mar 1 — the solver must leave Mar 1 free."""
    prev = [
        {"date": f"2026-02-{d}", "employee_id": 1, "shift_type_id": 1}
        for d in ("23", "24", "25", "26", "27")
    ]
    result = solve_schedule(_ctx(prev_assignments=prev))

    assert result.status in ("optimal", "feasible")
    ana_mar1 = next(
        a for a in result.assignments
        if a["employee_id"] == 1 and a["date"] == "2026-03-01"
    )
    assert ana_mar1["shift_type_id"] is None

    weekly_violations = [
        v for v in result.violations if v.rule_id == "max_weekly_hours"
    ]
    assert weekly_violations == []


def test_solver_violations_match_full_context_validation():
    """Violations reported by the solver must equal what the validate
    endpoint would report for the same schedule (including prev context)."""
    from app.services.validator import validate_schedule

    prev = [
        {"date": f"2026-02-{d}", "employee_id": 1, "shift_type_id": 1}
        for d in ("23", "24", "25", "26", "27")
    ]
    ctx = _ctx(prev_assignments=prev)
    result = solve_schedule(ctx)

    full_ctx = ScheduleContext(
        year=ctx.year,
        month=ctx.month,
        employees=ctx.employees,
        shift_types=ctx.shift_types,
        absences=ctx.absences,
        assignments=result.assignments,
        rules_config=ctx.rules_config,
        prev_assignments=prev,
    )
    expected = validate_schedule(full_ctx)

    def keys(violations):
        return sorted((v.rule_id, v.date, v.employee_id) for v in violations)

    assert keys(result.violations) == keys(expected)


def test_solver_min_consecutive_free_days_three():
    config = {
        **RELAXED_CONFIG,
        "min_consecutive_free_days": {"params": {"min_days": 3}},
    }
    result = solve_schedule(_ctx(rules_config=config))

    assert result.status in ("optimal", "feasible")
    free_day_violations = [
        v for v in result.violations if v.rule_id == "min_consecutive_free_days"
    ]
    assert free_day_violations == []


def test_solver_fixed_on_absent_day_is_ignored():
    """A pinned shift on a day the employee is absent must not make the
    whole model infeasible — the absence wins."""
    absences = [
        {"employee_id": 1, "start_date": "2026-03-01", "end_date": "2026-03-05", "type": "vacation"},
    ]
    fixed = [{"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1}]
    result = solve_schedule(_ctx(absences=absences), fixed=fixed)

    assert result.status in ("optimal", "feasible")
    ana_mar2 = [
        a for a in result.assignments
        if a["employee_id"] == 1 and a["date"] == "2026-03-02"
        and a["shift_type_id"] is not None
    ]
    assert ana_mar2 == []


def test_solver_respects_multiple_fixed():
    fixed = [
        {"date": "2026-03-01", "employee_id": 1, "shift_type_id": None},
        {"date": "2026-03-01", "employee_id": 2, "shift_type_id": 1},
        {"date": "2026-03-15", "employee_id": 3, "shift_type_id": 2},
    ]
    result = solve_schedule(_ctx(), fixed=fixed)

    assert result.status in ("optimal", "feasible")

    ana_1 = next(a for a in result.assignments if a["employee_id"] == 1 and a["date"] == "2026-03-01")
    assert ana_1["shift_type_id"] is None

    carlos_1 = next(a for a in result.assignments if a["employee_id"] == 2 and a["date"] == "2026-03-01")
    assert carlos_1["shift_type_id"] == 1

    maria_15 = next(a for a in result.assignments if a["employee_id"] == 3 and a["date"] == "2026-03-15")
    assert maria_15["shift_type_id"] == 2
