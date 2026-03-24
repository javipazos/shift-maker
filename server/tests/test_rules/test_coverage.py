from app.rules.base import ScheduleContext
from app.rules.coverage import PriorityShiftCoverage, WeekendShiftCoverage
from app.rules.rest import MinDailyCoverage


SHIFT_TYPES = [
    {"id": 1, "name": "Mañana", "start_time": "07:00", "end_time": "14:30", "effective_hours": 7.5, "priority_order": 1},
    {"id": 2, "name": "Tarde", "start_time": "14:30", "end_time": "22:00", "effective_hours": 7.5, "priority_order": 2},
]

EMPLOYEES = [
    {"id": 1, "name": "Ana", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 2, "name": "Carlos", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"id": 3, "name": "María", "hours_per_day": 8.0, "max_hours_per_week": 40.0},
]


def _ctx(assignments, absences=None, rules_config=None):
    return ScheduleContext(
        year=2026, month=3,
        employees=EMPLOYEES,
        shift_types=SHIFT_TYPES,
        absences=absences or [],
        assignments=assignments,
        rules_config=rules_config or {},
    )


class TestMinDailyCoverage:
    rule = MinDailyCoverage()

    def test_no_violations_when_coverage_met(self):
        """2 people working every day meets default min=2."""
        assignments = []
        for d in range(1, 32):
            date = f"2026-03-{d:02d}"
            assignments.append({"date": date, "employee_id": 1, "shift_type_id": 1})
            assignments.append({"date": date, "employee_id": 2, "shift_type_id": 2})

        violations = self.rule.validate(_ctx(assignments))
        assert len(violations) == 0

    def test_violation_on_uncovered_day(self):
        """Day with only 1 person working."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))

        march2_violations = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2_violations) == 1
        assert march2_violations[0].employee_id is None
        assert march2_violations[0].severity == "grave"
        assert "1 personas" in march2_violations[0].message

    def test_violation_on_day_with_no_assignments(self):
        """Day with 0 people working."""
        violations = self.rule.validate(_ctx([]))

        assert len(violations) == 31
        assert all(v.severity == "grave" for v in violations)

    def test_day_off_does_not_count_as_coverage(self):
        """Assignment with shift_type_id=None doesn't count."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-02", "employee_id": 2, "shift_type_id": None},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 1

    def test_structural_violation_when_insufficient_staff(self):
        """When absences leave fewer people available than min, violation is structural."""
        absences = [
            {"employee_id": 1, "start_date": "2026-03-02", "end_date": "2026-03-02"},
            {"employee_id": 2, "start_date": "2026-03-02", "end_date": "2026-03-02"},
        ]
        assignments = [
            {"date": "2026-03-02", "employee_id": 3, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments, absences=absences))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 1
        assert march2[0].resolvable is False

    def test_correctable_when_staff_available(self):
        """When there's enough staff but they're not assigned, it's correctable."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 1
        assert march2[0].resolvable is True

    def test_custom_minimum(self):
        """With weekday_min=1, 1 person is enough."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
        config = {"min_daily_coverage": {"params": {"weekday_min": 1, "weekend_min": 1}}}
        violations = self.rule.validate(_ctx(assignments, rules_config=config))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 0

    def test_weekend_uses_weekend_min(self):
        """Saturday March 7 2026 uses weekend_min."""
        assignments = [
            {"date": "2026-03-07", "employee_id": 1, "shift_type_id": 1},
        ]
        config = {"min_daily_coverage": {"params": {"weekday_min": 1, "weekend_min": 2}}}
        violations = self.rule.validate(_ctx(assignments, rules_config=config))
        march7 = [v for v in violations if v.date == "2026-03-07"]
        assert len(march7) == 1
        assert "fin de semana" in march7[0].message


class TestPriorityShiftCoverage:
    rule = PriorityShiftCoverage()

    def test_no_violation_higher_priority_covered(self):
        """Morning (priority 1) covered, afternoon not. OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 0

    def test_violation_lower_priority_covered_without_higher(self):
        """Afternoon (priority 2) covered but morning (priority 1) not. Violation."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 1
        assert "Mañana" in march2[0].message

    def test_no_violation_both_covered(self):
        """Both shifts covered. OK."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-02", "employee_id": 2, "shift_type_id": 2},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march2 = [v for v in violations if v.date == "2026-03-02"]
        assert len(march2) == 0


class TestWeekendShiftCoverage:
    rule = WeekendShiftCoverage()

    def test_violation_weekend_without_morning(self):
        """Saturday with only afternoon shift. Violation for missing morning."""
        # March 7 2026 is Saturday
        assignments = [
            {"date": "2026-03-07", "employee_id": 1, "shift_type_id": 2},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march7 = [v for v in violations if v.date == "2026-03-07" and v.rule_id == "weekend_shift_coverage"]
        assert len(march7) >= 1

    def test_no_violation_weekday(self):
        """Weekday with only afternoon. No weekend shift coverage violation."""
        assignments = [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
        ]
        violations = self.rule.validate(_ctx(assignments))
        march2 = [v for v in violations if v.date == "2026-03-02" and v.rule_id == "weekend_shift_coverage"]
        assert len(march2) == 0
