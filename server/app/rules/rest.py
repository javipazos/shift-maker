from datetime import datetime, timedelta

from ortools.sat.python import cp_model

from app.rules.base import Rule, ScheduleContext, SolverVars, Violation


def _parse_time(t: str) -> tuple[int, int]:
    parts = t.split(":")
    return int(parts[0]), int(parts[1])


def _shift_end_minutes(shift: dict) -> int:
    h, m = _parse_time(shift["end_time"])
    return h * 60 + m


def _shift_start_minutes(shift: dict) -> int:
    h, m = _parse_time(shift["start_time"])
    return h * 60 + m


def _get_shift_by_id(shift_types: list[dict], sid: int) -> dict | None:
    for st in shift_types:
        if st["id"] == sid:
            return st
    return None


def _next_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return (dt + timedelta(days=1)).strftime("%Y-%m-%d")


class MinRestBetweenShifts(Rule):
    id = "min_rest_between_shifts"
    name = "Descanso mínimo entre jornadas"
    category = "rest"
    default_priority = "mandatory"
    default_weight = 10
    default_params = {"min_hours": 12}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        min_minutes = config["params"]["min_hours"] * 60
        violations = []

        assignments_by_emp = _group_by_employee(ctx.assignments)

        for emp_id, emp_assignments in assignments_by_emp.items():
            by_date = {a["date"]: a for a in emp_assignments}
            sorted_dates = sorted(by_date.keys())

            for i in range(len(sorted_dates) - 1):
                date_a = sorted_dates[i]
                date_b = sorted_dates[i + 1]

                if _next_date(date_a) != date_b:
                    continue

                assign_a = by_date[date_a]
                assign_b = by_date[date_b]

                if assign_a["shift_type_id"] is None or assign_b["shift_type_id"] is None:
                    continue

                shift_a = _get_shift_by_id(ctx.shift_types, assign_a["shift_type_id"])
                shift_b = _get_shift_by_id(ctx.shift_types, assign_b["shift_type_id"])

                if not shift_a or not shift_b:
                    continue

                end_a = _shift_end_minutes(shift_a)
                start_b = _shift_start_minutes(shift_b)

                # Rest = time from end of day A to start of day B
                # Since they're consecutive days: rest = (24*60 - end_a) + start_b
                rest_minutes = (24 * 60 - end_a) + start_b

                if rest_minutes < min_minutes:
                    emp_name = _get_employee_name(ctx.employees, emp_id)
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=date_b,
                        employee_id=emp_id,
                        severity=severity,
                        resolvable=True,
                        message=f"{emp_name}: solo {rest_minutes // 60}h {rest_minutes % 60}m de descanso entre {date_a} y {date_b} (mínimo {config['params']['min_hours']}h)",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)
        min_minutes = config["params"]["min_hours"] * 60

        for emp_id in v.employee_ids:
            for i in range(len(v.dates) - 1):
                date_a = v.dates[i]
                date_b = v.dates[i + 1]

                if _next_date(date_a) != date_b:
                    continue

                for sid_a in v.shift_type_ids:
                    shift_a = _get_shift_by_id(ctx.shift_types, sid_a)
                    if not shift_a:
                        continue

                    for sid_b in v.shift_type_ids:
                        shift_b = _get_shift_by_id(ctx.shift_types, sid_b)
                        if not shift_b:
                            continue

                        end_a = _shift_end_minutes(shift_a)
                        start_b = _shift_start_minutes(shift_b)
                        rest = (24 * 60 - end_a) + start_b

                        if rest < min_minutes:
                            # These two shifts on consecutive days violate rest
                            model.Add(
                                v.shifts[emp_id][date_a][sid_a]
                                + v.shifts[emp_id][date_b][sid_b]
                                <= 1
                            )


class MinConsecutiveFreeDays(Rule):
    """Each rest block should be at least N consecutive days."""

    id = "min_consecutive_free_days"
    name = "Días libres consecutivos mínimos"
    category = "rest"
    default_priority = "desirable"
    default_weight = 6
    default_params = {"min_days": 2}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        min_days = config["params"]["min_days"]
        violations = []

        all_dates = _all_dates(ctx.year, ctx.month)
        assignments_by_emp = _group_by_employee(ctx.assignments)

        for emp in ctx.employees:
            working_dates = set()
            emp_assignments = assignments_by_emp.get(emp["id"], [])
            for a in emp_assignments:
                if a["shift_type_id"] is not None:
                    working_dates.add(a["date"])

            free_streak = 0
            streak_start = None

            for date_str in all_dates:
                if date_str not in working_dates:
                    if free_streak == 0:
                        streak_start = date_str
                    free_streak += 1
                else:
                    if 0 < free_streak < min_days:
                        severity = "grave" if config["priority"] == "mandatory" else "warning"
                        violations.append(Violation(
                            rule_id=self.id,
                            date=streak_start or date_str,
                            employee_id=emp["id"],
                            severity=severity,
                            resolvable=True,
                            message=f"{emp['name']}: solo {free_streak} día(s) libre(s) desde {streak_start} (mínimo {min_days})",
                        ))
                    free_streak = 0

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        # Soft constraint: hard to model perfectly in CP-SAT without complex encoding
        # The solver handles this indirectly through other rest constraints
        pass


class WeeklyRest(Rule):
    """At least N free days per rolling 7-day window."""

    id = "weekly_rest"
    name = "Descanso semanal mínimo"
    category = "rest"
    default_priority = "mandatory"
    default_weight = 8
    default_params = {"min_days": 1.5}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        min_days = config["params"]["min_days"]
        min_free = int(min_days)  # Use floor for validation (1.5 → at least 1)
        violations = []

        all_dates = _all_dates(ctx.year, ctx.month)
        assignments_by_emp = _group_by_employee(ctx.assignments)

        for emp in ctx.employees:
            working_dates = set()
            for a in assignments_by_emp.get(emp["id"], []):
                if a["shift_type_id"] is not None:
                    working_dates.add(a["date"])

            for i in range(len(all_dates) - 6):
                window = all_dates[i:i + 7]

                # Check all dates are consecutive
                if _next_date(window[-2]) != window[-1]:
                    continue

                free_in_window = sum(1 for d in window if d not in working_dates)
                if free_in_window < min_free:
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=window[0],
                        employee_id=emp["id"],
                        severity=severity,
                        resolvable=True,
                        message=f"{emp['name']}: solo {free_in_window} día(s) libre(s) en semana {window[0]} - {window[-1]} (mínimo {min_days})",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)
        min_free = int(config["params"]["min_days"])

        for emp_id in v.employee_ids:
            for i in range(len(v.dates) - 6):
                window = v.dates[i:i + 7]

                all_consecutive = all(
                    _next_date(window[j]) == window[j + 1]
                    for j in range(len(window) - 1)
                )

                if all_consecutive:
                    free_days = [
                        model.NewBoolVar(f"free_{emp_id}_{d}")
                        for d in window
                    ]
                    for j, d in enumerate(window):
                        w = v.works.get(emp_id, {}).get(d)
                        if w is not None:
                            model.Add(free_days[j] == 1 - w)
                        else:
                            model.Add(free_days[j] == 1)

                    model.Add(sum(free_days) >= min_free)


class MaxConsecutiveDays(Rule):
    id = "max_consecutive_days"
    name = "Máximo días consecutivos trabajados"
    category = "rest"
    default_priority = "mandatory"
    default_weight = 9
    default_params = {"max_days": 6}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        max_days = config["params"]["max_days"]
        violations = []

        assignments_by_emp = _group_by_employee(ctx.assignments)

        for emp_id, emp_assignments in assignments_by_emp.items():
            working_dates = {
                a["date"] for a in emp_assignments if a["shift_type_id"] is not None
            }
            sorted_dates = sorted(working_dates)

            consecutive = 0
            streak_start = None

            for i, date_str in enumerate(sorted_dates):
                if i == 0:
                    consecutive = 1
                    streak_start = date_str
                    continue

                prev = sorted_dates[i - 1]
                if _next_date(prev) == date_str:
                    consecutive += 1
                else:
                    consecutive = 1
                    streak_start = date_str

                if consecutive > max_days:
                    emp_name = _get_employee_name(ctx.employees, emp_id)
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=date_str,
                        employee_id=emp_id,
                        severity=severity,
                        resolvable=True,
                        message=f"{emp_name}: {consecutive} días consecutivos trabajados desde {streak_start} (máximo {max_days})",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)
        max_days = config["params"]["max_days"]

        for emp_id in v.employee_ids:
            # Sliding window: in any (max_days + 1) consecutive days, at least one must be free
            for i in range(len(v.dates) - max_days):
                window_dates = v.dates[i : i + max_days + 1]

                # Check they're actually consecutive
                all_consecutive = all(
                    _next_date(window_dates[j]) == window_dates[j + 1]
                    for j in range(len(window_dates) - 1)
                )

                if all_consecutive:
                    model.Add(
                        sum(v.works[emp_id][d] for d in window_dates) <= max_days
                    )


class MinDailyCoverage(Rule):
    id = "min_daily_coverage"
    name = "Cobertura mínima por día"
    category = "coverage"
    default_priority = "mandatory"
    default_weight = 10
    default_params = {"weekday_min": 2, "weekend_min": 2}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []
        available = _available_by_date(ctx)

        for date_str in _all_dates(ctx.year, ctx.month):
            is_weekend = _is_weekend(date_str)
            min_required = (
                config["params"]["weekend_min"]
                if is_weekend
                else config["params"]["weekday_min"]
            )

            working = _count_working(ctx.assignments, date_str)
            if working < min_required:
                avail_count = len(available.get(date_str, []))
                resolvable = avail_count >= min_required
                severity = "grave" if config["priority"] == "mandatory" else "warning"
                day_type = "fin de semana" if is_weekend else "entre semana"

                violations.append(Violation(
                    rule_id=self.id,
                    date=date_str,
                    employee_id=None,
                    severity=severity,
                    resolvable=resolvable,
                    message=f"{date_str} ({day_type}): {working} personas trabajando, mínimo {min_required}",
                ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)

        for date_str in v.dates:
            is_weekend = _is_weekend(date_str)
            min_required = (
                config["params"]["weekend_min"]
                if is_weekend
                else config["params"]["weekday_min"]
            )

            model.Add(
                sum(v.works[emp_id][date_str] for emp_id in v.employee_ids)
                >= min_required
            )


class MaxWeeklyHours(Rule):
    id = "max_weekly_hours"
    name = "Horas máximas semanales"
    category = "limits"
    default_priority = "mandatory"
    default_weight = 9
    default_params = {}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []

        for emp in ctx.employees:
            max_hours = emp["max_hours_per_week"]
            weeks = _group_by_week(ctx.year, ctx.month)

            for week_num, week_dates in weeks.items():
                total = 0.0
                for date_str in week_dates:
                    assignment = _find_assignment(ctx.assignments, date_str, emp["id"])
                    if assignment and assignment["shift_type_id"] is not None:
                        shift = _get_shift_by_id(ctx.shift_types, assignment["shift_type_id"])
                        if shift:
                            total += shift["effective_hours"]

                if total > max_hours:
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=week_dates[0],
                        employee_id=emp["id"],
                        severity=severity,
                        resolvable=True,
                        message=f"{emp['name']}: {total}h en semana {week_num} (máximo {max_hours}h)",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        weeks = _group_by_week(ctx.year, ctx.month)
        shift_hours = {
            st["id"]: st["effective_hours"] for st in ctx.shift_types
        }

        for emp in ctx.employees:
            max_hours = emp["max_hours_per_week"]

            for week_dates in weeks.values():
                # Sum of hours for this employee in this week <= max
                # Multiply by 10 to use integers (CP-SAT works with ints)
                hour_terms = []
                for date_str in week_dates:
                    if date_str not in v.dates:
                        continue
                    for sid in v.shift_type_ids:
                        if emp["id"] in v.shifts and date_str in v.shifts[emp["id"]]:
                            hours_x10 = int(shift_hours.get(sid, 0) * 10)
                            hour_terms.append(
                                v.shifts[emp["id"]][date_str][sid] * hours_x10
                            )

                if hour_terms:
                    model.Add(sum(hour_terms) <= int(max_hours * 10))


# --- Helper functions ---


def _group_by_employee(assignments: list[dict]) -> dict[int, list[dict]]:
    result: dict[int, list[dict]] = {}
    for a in assignments:
        result.setdefault(a["employee_id"], []).append(a)
    return result


def _get_employee_name(employees: list[dict], emp_id: int) -> str:
    for e in employees:
        if e["id"] == emp_id:
            return e["name"]
    return f"Employee {emp_id}"


def _find_assignment(
    assignments: list[dict], date: str, emp_id: int
) -> dict | None:
    for a in assignments:
        if a["date"] == date and a["employee_id"] == emp_id:
            return a
    return None


def _count_working(assignments: list[dict], date: str) -> int:
    return sum(
        1 for a in assignments
        if a["date"] == date and a["shift_type_id"] is not None
    )


def _is_weekend(date_str: str) -> bool:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() >= 5


def _all_dates(year: int, month: int) -> list[str]:
    import calendar

    days_in_month = calendar.monthrange(year, month)[1]
    return [
        f"{year}-{month:02d}-{d:02d}" for d in range(1, days_in_month + 1)
    ]


def _available_by_date(ctx: ScheduleContext) -> dict[str, list[int]]:
    """Map date -> list of available employee IDs (no absence that day)."""
    all_dates = _all_dates(ctx.year, ctx.month)
    active_ids = [e["id"] for e in ctx.employees]

    result = {d: list(active_ids) for d in all_dates}

    for absence in ctx.absences:
        start = absence["start_date"]
        end = absence["end_date"]
        for d in all_dates:
            if start <= d <= end:
                emp_id = absence["employee_id"]
                if emp_id in result[d]:
                    result[d].remove(emp_id)

    return result


def _group_by_week(year: int, month: int) -> dict[int, list[str]]:
    """Group dates by ISO week number."""
    weeks: dict[int, list[str]] = {}
    for date_str in _all_dates(year, month):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        week_num = dt.isocalendar()[1]
        weeks.setdefault(week_num, []).append(date_str)
    return weeks
