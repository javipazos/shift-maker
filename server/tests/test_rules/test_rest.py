import pytest

from app.rules.base import ScheduleContext
from app.rules.rest import MinRestBetweenShifts, MaxConsecutiveDays, MinConsecutiveFreeDays, WeeklyRest


SHIFT_TYPES = [
    {"id": 1, "name": "Mañana", "start_time": "07:00", "end_time": "14:30", "effective_hours": 7.5, "priority_order": 1},
    {"id": 2, "name": "Tarde", "start_time": "14:30", "end_time": "22:00", "effective_hours": 7.5, "priority_order": 2},
    {"id": 3, "name": "Media mañana", "start_time": "09:00", "end_time": "13:00", "effective_hours": 4.0, "priority_order": 3},
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


class TestMinRestBetweenShifts:
    rule = MinRestBetweenShifts()

    def test_no_violation_morning_to_morning(self):
        """Morning → Morning next day = 16.5h rest. OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_violation_afternoon_to_morning(self):
        """Afternoon (ends 22:00) → Morning (starts 07:00) = 9h rest. Violation."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].employee_id == 1
        assert violations[0].date == "2026-03-03"
        assert violations[0].severity == "grave"
        assert violations[0].resolvable is True
        assert "9h" in violations[0].message

    def test_no_violation_morning_to_afternoon(self):
        """Morning (ends 14:30) → Afternoon (starts 14:30) = 24h rest. OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 2},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_no_violation_non_consecutive_days(self):
        """Afternoon → Morning but with a day gap. OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-03-04", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_no_violation_day_off_between(self):
        """Afternoon, free day, morning. No violation."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": None},
            {"date": "2026-03-04", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_multiple_employees_independent(self):
        """Violation for one employee, not the other."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-02", "employee_id": 2, "shift_type_id": 1},
            {"date": "2026-03-03", "employee_id": 2, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].employee_id == 1

    def test_custom_min_hours(self):
        """With 8h min rest, afternoon→morning (9h rest) is OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 1},
        ]
        config = {"min_rest_between_shifts": {"params": {"min_hours": 8}}}
        violations = self.rule.validate(_ctx(assignments, config))
        assert len(violations) == 0

    def test_severity_follows_priority_config(self):
        """When rule is desirable, violations are warnings."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": 1},
        ]
        config = {"min_rest_between_shifts": {"priority": "desirable"}}
        violations = self.rule.validate(_ctx(assignments, config))
        assert violations[0].severity == "warning"


class TestMaxConsecutiveDays:
    rule = MaxConsecutiveDays()

    def test_no_violation_under_limit(self):
        """5 consecutive days with default max=6. OK."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_no_violation_at_limit(self):
        """Exactly 6 consecutive days. OK."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 8)
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_violation_over_limit(self):
        """7 consecutive days. Violation on day 7."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 9)
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].date == "2026-03-08"
        assert violations[0].employee_id == 1
        assert "7" in violations[0].message

    def test_violation_continues_accumulating(self):
        """8 consecutive days produces violations on days 7 and 8."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 10)
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 2

    def test_day_off_breaks_streak(self):
        """6 days, day off, 6 days. No violation."""
        days_first = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 8)
        ]
        day_off = [{"date": "2026-03-08", "employee_id": 1, "shift_type_id": None}]
        days_second = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(9, 15)
        ]
        violations = self.rule.validate(_ctx(days_first + day_off + days_second))
        assert len(violations) == 0

    def test_custom_max_days(self):
        """With max=4, 5 consecutive days violates."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ]
        config = {"max_consecutive_days": {"params": {"max_days": 4}}}
        violations = self.rule.validate(_ctx(assignments, config))
        assert len(violations) == 1

    def test_multiple_employees_independent(self):
        """Each employee tracked separately."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 9)
        ] + [
            {"date": f"2026-03-{d:02d}", "employee_id": 2, "shift_type_id": 1}
            for d in range(2, 7)
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 1
        assert violations[0].employee_id == 1


class TestMinConsecutiveFreeDays:
    rule = MinConsecutiveFreeDays()

    def test_no_violation_two_consecutive_free_days(self):
        """Work Mon-Fri (2-6), free Sat-Sun (7-8). No violation for the weekend block."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ] + [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(9, 14)
        ]
        violations = self.rule.validate(_ctx(assignments))
        # Only March 1 (isolated) should be a violation, not the Sat-Sun blocks
        emp1 = [v for v in violations if v.employee_id == 1]
        weekend_violations = [v for v in emp1 if "2026-03-07" in v.date or "2026-03-08" in v.date]
        assert len(weekend_violations) == 0

    def test_violation_single_isolated_free_day(self):
        """Work, 1 free, work. Violation: isolated free day."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-04", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        emp1 = [v for v in violations if v.employee_id == 1 and v.rule_id == "min_consecutive_free_days"]
        assert len(emp1) >= 1


class TestWeeklyRest:
    rule = WeeklyRest()

    def test_no_violation_with_rest_days(self):
        """5 work days + 2 free in a 7-day window. OK."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ]
        violations = self.rule.validate(_ctx(assignments))
        weekly = [v for v in violations if v.employee_id == 1]
        assert len(weekly) == 0

    def test_violation_seven_consecutive_work_days(self):
        """7 consecutive work days = 0 free in window. Violation."""
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 9)
        ]
        violations = self.rule.validate(_ctx(assignments))
        weekly = [v for v in violations if v.rule_id == "weekly_rest" and v.employee_id == 1]
        assert len(weekly) >= 1
