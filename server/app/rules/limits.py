from ortools.sat.python import cp_model

from app.rules.base import Rule, ScheduleContext, SolverVars, Violation
from app.rules.rest import (
    _all_dates,
    _find_assignment,
    _get_shift_by_id,
)


class MaxDailyHours(Rule):
    """No shift should exceed max daily hours."""

    id = "max_daily_hours"
    name = "Horas máximas diarias"
    category = "limits"
    default_priority = "mandatory"
    default_weight = 8
    default_params = {"max_hours": 9}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        max_hours = config["params"]["max_hours"]
        violations = []

        for emp in ctx.employees:
            for date_str in _all_dates(ctx.year, ctx.month):
                assignment = _find_assignment(ctx.assignments, date_str, emp["id"])
                if not assignment or assignment["shift_type_id"] is None:
                    continue

                shift = _get_shift_by_id(ctx.shift_types, assignment["shift_type_id"])
                if shift and shift["effective_hours"] > max_hours:
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=date_str,
                        employee_id=emp["id"],
                        severity=severity,
                        resolvable=True,
                        message=f"{emp['name']}: {shift['effective_hours']}h en {date_str} (máximo {max_hours}h/día)",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)
        max_hours = config["params"]["max_hours"]

        for st in ctx.shift_types:
            if st["effective_hours"] > max_hours:
                # Forbid this shift type entirely
                for emp_id in v.employee_ids:
                    for date_str in v.dates:
                        if date_str in v.shifts.get(emp_id, {}):
                            model.Add(v.shifts[emp_id][date_str][st["id"]] == 0)


class RequestedDaysOff(Rule):
    """Respect personal absence requests (modeled as absences of type 'personal')."""

    id = "requested_days_off"
    name = "Días libres pedidos"
    category = "limits"
    default_priority = "mandatory"
    default_weight = 10
    default_params = {}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []

        personal_absences = [
            a for a in ctx.absences if a["type"] == "personal"
        ]

        for absence in personal_absences:
            for date_str in _all_dates(ctx.year, ctx.month):
                if absence["start_date"] <= date_str <= absence["end_date"]:
                    assignment = _find_assignment(
                        ctx.assignments, date_str, absence["employee_id"]
                    )
                    if assignment and assignment["shift_type_id"] is not None:
                        emp_name = next(
                            (e["name"] for e in ctx.employees if e["id"] == absence["employee_id"]),
                            f"ID {absence['employee_id']}",
                        )
                        severity = "grave" if config["priority"] == "mandatory" else "warning"
                        violations.append(Violation(
                            rule_id=self.id,
                            date=date_str,
                            employee_id=absence["employee_id"],
                            severity=severity,
                            resolvable=True,
                            message=f"{emp_name}: trabaja {date_str} pero tiene día libre pedido",
                        ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        # Already handled by _build_absent_set in solver — absences are fixed to 0
        pass
