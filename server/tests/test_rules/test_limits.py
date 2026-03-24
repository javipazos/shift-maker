from app.rules.base import ScheduleContext
from app.rules.limits import MaxDailyHours, RequestedDaysOff
from app.rules.rest import MaxWeeklyHours


SHIFT_TYPES = [
    {"id": 1, "name": "Mañana", "start_time": "07:00", "end_time": "14:30", "effective_hours": 7.5, "priority_order": 1},
    {"id": 2, "name": "Tarde", "start_time": "14:30", "end_time": "22:00", "effective_hours": 7.5, "priority_order": 2},
    {"id": 3, "name": "Media mañana", "start_time": "09:00", "end_time": "13:00", "effective_hours": 4.0, "priority_order": 3},
]

EMPLOYEES = [
    {"id": 1, "name": "Ana", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 2, "name": "Pedro", "hours_per_day": 4.0, "max_hours_per_week": 20.0},
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


class TestMaxWeeklyHours:
    rule = MaxWeeklyHours()

    def test_no_violation_under_limit(self):
        """5 morning shifts = 37.5h exactly at limit for Ana."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)  # Mon-Fri
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_violation_over_limit(self):
        """6 morning shifts = 45h, over 37.5h limit for Ana."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 8)  # Mon-Sat
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].employee_id == 1
        assert "45" in violations[0].message

    def test_part_time_employee_lower_limit(self):
        """Pedro (20h/week max) with 6 half-morning shifts = 24h. Violation."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 2, "shift_type_id": 3}
            for d in range(2, 8)  # 6 days * 4h = 24h
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].employee_id == 2

    def test_part_time_under_limit(self):
        """Pedro with 5 half-morning shifts = 20h. Exactly at limit."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 2, "shift_type_id": 3}
            for d in range(2, 7)  # 5 days * 4h = 20h
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_day_off_not_counted(self):
        """Day off (shift_type_id=None) doesn't add hours."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ] + [
            {"date": "2026-03-07", "employee_id": 1, "shift_type_id": None},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_multiple_employees_independent(self):
        """Ana over limit, Pedro under limit — only one violation."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 8)
        ] + [
            {"date": f"2026-03-{d:02d}", "employee_id": 2, "shift_type_id": 3}
            for d in range(2, 7)
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].employee_id == 1

    def test_different_weeks_checked_separately(self):
        """5 morning shifts in week 1 + 5 in week 2 = 37.5h each week. OK."""
        week1 = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ]
        week2 = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(9, 14)
        ]
        violations = self.rule.validate(_ctx(week1 + week2))
        assert len(violations) == 0


class TestMaxDailyHours:
    rule = MaxDailyHours()

    def test_no_violation_normal_shift(self):
        """7.5h shift with 9h max. OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        daily = [v for v in violations if v.rule_id == "max_daily_hours"]
        assert len(daily) == 0

    def test_violation_long_shift(self):
        """Shift with 10h > 9h max. Violation."""
        long_shift_types = SHIFT_TYPES + [
            {"id": 4, "name": "Larga", "start_time": "07:00", "end_time": "17:00", "effective_hours": 10.0, "priority_order": 4},
        ]
        ctx = ScheduleContext(
            year=2026, month=3,
            employees=EMPLOYEES,
            shift_types=long_shift_types,
            absences=[],
            assignments=[{"date": "2026-03-02", "employee_id": 1, "shift_type_id": 4}],
            rules_config={},
        )
        violations = self.rule.validate(ctx)
        daily = [v for v in violations if v.rule_id == "max_daily_hours"]
        assert len(daily) == 1


class TestRequestedDaysOff:
    rule = RequestedDaysOff()

    def test_violation_works_on_requested_day(self):
        """Employee works on a day they requested off. Violation."""
        ctx = ScheduleContext(
            year=2026, month=3,
            employees=EMPLOYEES,
            shift_types=SHIFT_TYPES,
            absences=[{"employee_id": 1, "start_date": "2026-03-10", "end_date": "2026-03-10", "type": "personal"}],
            assignments=[{"date": "2026-03-10", "employee_id": 1, "shift_type_id": 1}],
            rules_config={},
        )
        violations = self.rule.validate(ctx)
        assert len(violations) == 1
        assert violations[0].employee_id == 1

    def test_no_violation_vacation_type(self):
        """Vacation absences are not checked by this rule (handled by solver)."""
        ctx = ScheduleContext(
            year=2026, month=3,
            employees=EMPLOYEES,
            shift_types=SHIFT_TYPES,
            absences=[{"employee_id": 1, "start_date": "2026-03-10", "end_date": "2026-03-10", "type": "vacation"}],
            assignments=[{"date": "2026-03-10", "employee_id": 1, "shift_type_id": 1}],
            rules_config={},
        )
        violations = self.rule.validate(ctx)
        assert len(violations) == 0

    def test_no_violation_when_free(self):
        """Employee is free on requested day. OK."""
        ctx = ScheduleContext(
            year=2026, month=3,
            employees=EMPLOYEES,
            shift_types=SHIFT_TYPES,
            absences=[{"employee_id": 1, "start_date": "2026-03-10", "end_date": "2026-03-10", "type": "personal"}],
            assignments=[],
            rules_config={},
        )
        violations = self.rule.validate(ctx)
        assert len(violations) == 0
