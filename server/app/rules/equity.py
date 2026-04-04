from datetime import datetime

from ortools.sat.python import cp_model

from app.rules.base import Rule, ScheduleContext, SolverVars, Violation
from app.rules.rest import (
    _all_dates,
    _find_assignment,
    _get_shift_by_id,
    _is_weekend,
)


class MonthlyFreeWeekend(Rule):
    """Each employee should have at least N complete free weekends per month."""

    id = "monthly_free_weekend"
    name = "Fin de semana libre mensual"
    category = "equity"
    default_priority = "desirable"
    default_weight = 7
    default_params = {"min_free_weekends": 1}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        min_free = config["params"]["min_free_weekends"]
        violations = []
        weekends = _get_weekends(ctx.year, ctx.month)

        for emp in ctx.employees:
            free_count = 0
            for sat, sun in weekends:
                sat_assign = _find_assignment(ctx.assignments, sat, emp["id"])
                sun_assign = _find_assignment(ctx.assignments, sun, emp["id"])

                sat_works = sat_assign and sat_assign["shift_type_id"] is not None
                sun_works = sun_assign and sun_assign["shift_type_id"] is not None

                if not sat_works and not sun_works:
                    free_count += 1

            if free_count < min_free:
                severity = "grave" if config["priority"] == "mandatory" else "warning"
                violations.append(Violation(
                    rule_id=self.id,
                    date=weekends[0][0] if weekends else "",
                    employee_id=emp["id"],
                    severity=severity,
                    resolvable=True,
                    message=f"{emp['name']}: {free_count} fines de semana libres (mínimo {min_free})",
                ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)
        min_free = config["params"]["min_free_weekends"]
        weekends = _get_weekends(ctx.year, ctx.month)

        for emp_id in v.employee_ids:
            weekend_free_vars = []

            for sat, sun in weekends:
                if sat not in v.dates or sun not in v.dates:
                    continue

                # free_weekend = 1 iff both sat and sun are free
                free_var = model.NewBoolVar(f"free_we_{emp_id}_{sat}")
                sat_works = v.works.get(emp_id, {}).get(sat)
                sun_works = v.works.get(emp_id, {}).get(sun)

                if sat_works is not None and sun_works is not None:
                    # free_var = 1 iff sat_works=0 AND sun_works=0
                    model.Add(sat_works + sun_works == 0).OnlyEnforceIf(free_var)
                    model.Add(sat_works + sun_works >= 1).OnlyEnforceIf(free_var.Not())
                    weekend_free_vars.append(free_var)

            if weekend_free_vars:
                # Soft: penalize in objective if not enough free weekends
                model.Add(sum(weekend_free_vars) >= min_free)


class WeekendDistribution(Rule):
    """Distribute worked weekends as evenly as possible."""

    id = "weekend_distribution"
    name = "Distribución equitativa de fines de semana"
    category = "equity"
    default_priority = "desirable"
    default_weight = 6
    default_params = {}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []
        weekends = _get_weekends(ctx.year, ctx.month)

        worked_weekends = {}
        for emp in ctx.employees:
            count = 0
            for sat, sun in weekends:
                sat_a = _find_assignment(ctx.assignments, sat, emp["id"])
                sun_a = _find_assignment(ctx.assignments, sun, emp["id"])
                if (sat_a and sat_a["shift_type_id"]) or (sun_a and sun_a["shift_type_id"]):
                    count += 1
            worked_weekends[emp["id"]] = count

        if not worked_weekends:
            return violations

        max_we = max(worked_weekends.values())
        min_we = min(worked_weekends.values())

        if max_we - min_we > 1:
            severity = "grave" if config["priority"] == "mandatory" else "warning"
            for emp in ctx.employees:
                if worked_weekends[emp["id"]] == max_we:
                    violations.append(Violation(
                        rule_id=self.id,
                        date="",
                        employee_id=emp["id"],
                        severity=severity,
                        resolvable=True,
                        message=f"{emp['name']}: trabaja {max_we} fines de semana (otros trabajan {min_we})",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        weekends = _get_weekends(ctx.year, ctx.month)

        weekend_work_counts = {}
        for emp_id in v.employee_ids:
            weekend_vars = []
            for sat, sun in weekends:
                if sat not in v.dates or sun not in v.dates:
                    continue

                works_we = model.NewBoolVar(f"works_we_{emp_id}_{sat}")
                sat_w = v.works.get(emp_id, {}).get(sat)
                sun_w = v.works.get(emp_id, {}).get(sun)

                if sat_w is not None and sun_w is not None:
                    model.Add(sat_w + sun_w >= 1).OnlyEnforceIf(works_we)
                    model.Add(sat_w + sun_w == 0).OnlyEnforceIf(works_we.Not())
                    weekend_vars.append(works_we)

            if weekend_vars:
                weekend_work_counts[emp_id] = sum(weekend_vars)

        # Hard constraint: no employee works more than 1 extra weekend vs others
        if len(weekend_work_counts) >= 2:
            emp_ids = list(weekend_work_counts.keys())
            for i in range(len(emp_ids)):
                for j in range(i + 1, len(emp_ids)):
                    model.Add(
                        weekend_work_counts[emp_ids[i]]
                        - weekend_work_counts[emp_ids[j]]
                        <= 1
                    )
                    model.Add(
                        weekend_work_counts[emp_ids[j]]
                        - weekend_work_counts[emp_ids[i]]
                        <= 1
                    )


class HoursDistribution(Rule):
    """Distribute total hours proportionally to each employee's contract."""

    id = "hours_distribution"
    name = "Distribución equitativa de horas"
    category = "equity"
    default_priority = "desirable"
    default_weight = 6
    default_params = {}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []

        hours_per_emp = {}
        for emp in ctx.employees:
            total = 0.0
            for a in ctx.assignments:
                if a["employee_id"] == emp["id"] and a["shift_type_id"] is not None:
                    shift = _get_shift_by_id(ctx.shift_types, a["shift_type_id"])
                    if shift:
                        total += shift["effective_hours"]
            hours_per_emp[emp["id"]] = total

        # Calculate expected ratio vs actual
        for emp in ctx.employees:
            if emp["max_hours_per_week"] <= 0:
                continue

            actual = hours_per_emp.get(emp["id"], 0)
            # Rough expected: (max_hours_per_week / 7) * days_in_month
            import calendar
            days = calendar.monthrange(ctx.year, ctx.month)[1]
            expected = (emp["max_hours_per_week"] / 7) * days

            deviation = abs(actual - expected) / max(expected, 1)
            if deviation > 0.15:
                severity = "grave" if config["priority"] == "mandatory" else "warning"
                violations.append(Violation(
                    rule_id=self.id,
                    date="",
                    employee_id=emp["id"],
                    severity=severity,
                    resolvable=True,
                    message=f"{emp['name']}: {actual:.1f}h trabajadas, esperadas ~{expected:.0f}h ({deviation:.0%} desviación)",
                ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        # Equity constraints are primarily handled via the objective function
        # The solver naturally distributes work through max_weekly_hours constraints
        pass


def _get_weekends(year: int, month: int) -> list[tuple[str, str]]:
    """Return list of (saturday, sunday) date pairs in the month."""
    weekends = []
    dates = _all_dates(year, month)

    for date_str in dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.weekday() == 5:  # Saturday
            sunday = f"{year}-{month:02d}-{dt.day + 1:02d}"
            if sunday in dates:
                weekends.append((date_str, sunday))

    return weekends
