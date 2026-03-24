from app.rules.base import ScheduleContext
from app.rules.equity import MonthlyFreeWeekend, WeekendDistribution


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


class TestMonthlyFreeWeekend:
    rule = MonthlyFreeWeekend()

    def test_violation_no_free_weekends(self):
        """Employee works every weekend day. Violation."""
        # March 2026 weekends: 7-8, 14-15, 21-22, 28-29
        weekend_days = [7, 8, 14, 15, 21, 22, 28, 29]
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in weekend_days
        ]
        violations = self.rule.validate(_ctx(assignments))
        emp1 = [v for v in violations if v.employee_id == 1]
        assert len(emp1) == 1
        assert "0 fines de semana libres" in emp1[0].message

    def test_no_violation_one_free_weekend(self):
        """Employee has one free weekend (both sat+sun free). OK."""
        # Work 3 weekends, free the 4th (28-29)
        weekend_days = [7, 8, 14, 15, 21, 22]
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in weekend_days
        ]
        violations = self.rule.validate(_ctx(assignments))
        emp1 = [v for v in violations if v.employee_id == 1]
        assert len(emp1) == 0

    def test_partial_weekend_doesnt_count(self):
        """Saturday free but Sunday worked = NOT a free weekend."""
        # Free on Saturdays, work on Sundays
        sunday_days = [8, 15, 22, 29]
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in sunday_days
        ]
        violations = self.rule.validate(_ctx(assignments))
        emp1 = [v for v in violations if v.employee_id == 1]
        assert len(emp1) == 1


class TestWeekendDistribution:
    rule = WeekendDistribution()

    def test_no_violation_equal_distribution(self):
        """Both employees work same number of weekends. OK."""
        assignments = [
            {"date": "2026-03-07", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-08", "employee_id": 2, "shift_type_id": 1},
            {"date": "2026-03-14", "employee_id": 2, "shift_type_id": 1},
            {"date": "2026-03-15", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_violation_unequal_distribution(self):
        """One employee works 3 weekends, other works 0. Violation."""
        weekend_days = [7, 8, 14, 15, 21, 22]
        assignments = [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in weekend_days
        ]
        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) >= 1
        assert any(v.employee_id == 1 for v in violations)
