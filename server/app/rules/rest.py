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
        first_date = f"{ctx.year}-{ctx.month:02d}-01"

        assignments_by_emp = _group_by_employee(_all_assignments(ctx))

        for emp_id, emp_assignments in assignments_by_emp.items():
            by_date = {a["date"]: a for a in emp_assignments}
            sorted_dates = sorted(by_date.keys())

            for i in range(len(sorted_dates) - 1):
                date_a = sorted_dates[i]
                date_b = sorted_dates[i + 1]

                if date_b < first_date:
                    continue

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
        enforce = self.make_enforcer(model, v, ctx)
        min_minutes = config["params"]["min_hours"] * 60
        dates = v.context_dates or v.dates

        for emp_id in v.employee_ids:
            for i in range(len(dates) - 1):
                date_a = dates[i]
                date_b = dates[i + 1]

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
                            enforce(model.Add(
                                v.shifts[emp_id][date_a][sid_a]
                                + v.shifts[emp_id][date_b][sid_b]
                                <= 1
                            ))


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
        first_date = f"{ctx.year}-{ctx.month:02d}-01"

        all_dates = _context_dates(ctx)
        assignments_by_emp = _group_by_employee(_all_assignments(ctx))

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
                    if 0 < free_streak < min_days and date_str >= first_date:
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
        config = self.get_config(ctx)
        enforce = self.make_enforcer(model, v, ctx)
        min_days = int(config["params"]["min_days"])
        dates = v.context_dates or v.dates

        # A free block of length k < min_days means: work, k free days, work.
        # Forbid that pattern for every k below the minimum.
        for emp_id in v.employee_ids:
            for free_block_len in range(1, min_days):
                for window in _consecutive_windows(dates, free_block_len + 2):
                    first, *middle, last = window
                    enforce(model.Add(
                        v.works[emp_id][first]
                        - sum(v.works[emp_id][m] for m in middle)
                        + v.works[emp_id][last]
                        <= 1
                    ))


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
        min_free = int(min_days)
        violations = []
        first_date = f"{ctx.year}-{ctx.month:02d}-01"

        all_dates = _context_dates(ctx)
        assignments_by_emp = _group_by_employee(_all_assignments(ctx))

        for emp in ctx.employees:
            working_dates = set()
            for a in assignments_by_emp.get(emp["id"], []):
                if a["shift_type_id"] is not None:
                    working_dates.add(a["date"])

            for i in range(len(all_dates) - 6):
                window = all_dates[i:i + 7]

                if window[-1] < first_date:
                    continue

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
        enforce = self.make_enforcer(model, v, ctx)
        min_free = int(config["params"]["min_days"])
        dates = v.context_dates or v.dates

        for emp_id in v.employee_ids:
            for i in range(len(dates) - 6):
                window = dates[i:i + 7]

                all_consecutive = all(
                    _next_date(window[j]) == window[j + 1]
                    for j in range(len(window) - 1)
                )

                if all_consecutive:
                    free_days = [
                        model.NewBoolVar(f"free_{emp_id}_{i}_{d}")
                        for d in window
                    ]
                    for j, d in enumerate(window):
                        w = v.works.get(emp_id, {}).get(d)
                        if w is not None:
                            model.Add(free_days[j] == 1 - w)
                        else:
                            model.Add(free_days[j] == 1)

                    enforce(model.Add(sum(free_days) >= min_free))


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
        first_date = f"{ctx.year}-{ctx.month:02d}-01"

        assignments_by_emp = _group_by_employee(_all_assignments(ctx))

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

                if consecutive > max_days and date_str >= first_date:
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
        enforce = self.make_enforcer(model, v, ctx)
        max_days = config["params"]["max_days"]
        dates = v.context_dates or v.dates

        for emp_id in v.employee_ids:
            for window_dates in _consecutive_windows(dates, max_days + 1):
                enforce(model.Add(
                    sum(v.works[emp_id][d] for d in window_dates) <= max_days
                ))


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
        enforce = self.make_enforcer(model, v, ctx)

        for date_str in v.dates:
            is_weekend = _is_weekend(date_str)
            min_required = (
                config["params"]["weekend_min"]
                if is_weekend
                else config["params"]["weekday_min"]
            )

            enforce(model.Add(
                sum(v.works[emp_id][date_str] for emp_id in v.employee_ids)
                >= min_required
            ))


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
        merged = _all_assignments(ctx)

        for emp in ctx.employees:
            max_hours = emp["max_hours_per_week"]
            weeks = _group_by_week_from_dates(_context_dates(ctx))

            for week_num, week_dates in weeks.items():
                total = 0.0
                for date_str in week_dates:
                    assignment = _find_assignment(merged, date_str, emp["id"])
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
        enforce = self.make_enforcer(model, v, ctx)
        shift_hours = {
            st["id"]: st["effective_hours"] for st in ctx.shift_types
        }
        weeks = _group_by_week_from_dates(_context_dates(ctx))

        for emp in ctx.employees:
            for week_dates in weeks.values():
                current_dates = [d for d in week_dates if d in v.dates]
                if not current_dates:
                    continue

                prev_x10 = _prev_week_hours_x10(ctx, emp["id"], week_dates)
                # The past can already exceed the limit (manual edits); clamp
                # to zero so the model stays feasible and just blocks new work.
                budget_x10 = max(int(emp["max_hours_per_week"] * 10) - prev_x10, 0)

                emp_shifts = v.shifts.get(emp["id"], {})
                hour_terms = _hour_terms_x10(emp_shifts, current_dates, shift_hours)
                if hour_terms:
                    enforce(model.Add(sum(hour_terms) <= budget_x10))


# --- Helper functions ---


def _consecutive_windows(dates: list[str], size: int):
    for i in range(len(dates) - size + 1):
        window = dates[i : i + size]
        is_consecutive = all(
            _next_date(window[j]) == window[j + 1] for j in range(size - 1)
        )
        if is_consecutive:
            yield window


def _prev_week_hours_x10(ctx: ScheduleContext, emp_id: int, week_dates: list[str]) -> int:
    shift_hours = {st["id"]: st["effective_hours"] for st in ctx.shift_types}
    week_set = set(week_dates)
    total = 0.0

    for a in ctx.prev_assignments:
        if a["employee_id"] != emp_id or a["date"] not in week_set:
            continue
        if a["shift_type_id"] is None:
            continue
        total += shift_hours.get(a["shift_type_id"], 0)

    return int(total * 10)


def _hour_terms_x10(
    emp_shifts: dict[str, dict[int, object]],
    dates: list[str],
    shift_hours: dict[int, float],
) -> list:
    # CP-SAT only handles integers, so hours are scaled by 10
    terms = []
    for date_str in dates:
        for sid, var in emp_shifts.get(date_str, {}).items():
            terms.append(var * int(shift_hours.get(sid, 0) * 10))
    return terms


def _all_assignments(ctx: ScheduleContext) -> list[dict]:
    """Merge previous month context with current assignments."""
    return ctx.prev_assignments + ctx.assignments


def _context_dates(ctx: ScheduleContext) -> list[str]:
    """Previous context dates + current month dates, sorted."""
    prev_dates = sorted({a["date"] for a in ctx.prev_assignments})
    return prev_dates + _all_dates(ctx.year, ctx.month)


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


def _group_by_week_from_dates(dates: list[str]) -> dict[int, list[str]]:
    """Group arbitrary date list by ISO week number."""
    weeks: dict[int, list[str]] = {}
    for date_str in dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        week_num = dt.isocalendar()[1]
        weeks.setdefault(week_num, []).append(date_str)
    return weeks
