from ortools.sat.python import cp_model

from app.rules.base import Rule, ScheduleContext, SolverVars, Violation
from app.rules.rest import (
    _all_dates,
    _available_by_date,
    _count_working,
    _get_employee_name,
    _get_shift_by_id,
    _is_weekend,
)


class WeekendShiftCoverage(Rule):
    """Each required shift type must be covered on weekends."""

    id = "weekend_shift_coverage"
    name = "Cobertura por turno en fin de semana"
    category = "coverage"
    default_priority = "mandatory"
    default_weight = 8
    default_params = {"required_shifts": ["morning", "afternoon"]}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []

        shift_name_to_id = {st["name"].lower(): st["id"] for st in ctx.shift_types}

        for date_str in _all_dates(ctx.year, ctx.month):
            if not _is_weekend(date_str):
                continue

            day_assignments = [
                a for a in ctx.assignments
                if a["date"] == date_str and a["shift_type_id"] is not None
            ]
            covered_ids = {a["shift_type_id"] for a in day_assignments}

            for shift_name in config["params"].get("required_shifts", []):
                # Match by priority order: "morning" = priority 1, "afternoon" = priority 2
                target_shift = _find_shift_by_keyword(ctx.shift_types, shift_name)
                if not target_shift:
                    continue

                if target_shift["id"] not in covered_ids:
                    available = _available_by_date(ctx).get(date_str, [])
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=date_str,
                        employee_id=None,
                        severity=severity,
                        resolvable=len(available) > len(day_assignments),
                        message=f"{date_str}: turno {target_shift['name']} sin cubrir en fin de semana",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)

        for date_str in v.dates:
            if not _is_weekend(date_str):
                continue

            for shift_name in config["params"].get("required_shifts", []):
                target = _find_shift_by_keyword(ctx.shift_types, shift_name)
                if not target or target["id"] not in v.shift_type_ids:
                    continue

                model.Add(
                    sum(
                        v.shifts[eid][date_str][target["id"]]
                        for eid in v.employee_ids
                        if date_str in v.shifts.get(eid, {})
                    )
                    >= 1
                )


class MinPerShiftCoverage(Rule):
    """Each active shift type should have at least N people."""

    id = "min_per_shift_coverage"
    name = "Cobertura mínima por turno"
    category = "coverage"
    default_priority = "desirable"
    default_weight = 5
    default_params = {"min_per_shift": 1}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        min_per = config["params"]["min_per_shift"]
        violations = []

        for date_str in _all_dates(ctx.year, ctx.month):
            for st in ctx.shift_types:
                count = sum(
                    1 for a in ctx.assignments
                    if a["date"] == date_str and a["shift_type_id"] == st["id"]
                )
                if count < min_per:
                    available = _available_by_date(ctx).get(date_str, [])
                    severity = "grave" if config["priority"] == "mandatory" else "warning"
                    violations.append(Violation(
                        rule_id=self.id,
                        date=date_str,
                        employee_id=None,
                        severity=severity,
                        resolvable=len(available) >= min_per * len(ctx.shift_types),
                        message=f"{date_str}: turno {st['name']} tiene {count} personas (mínimo {min_per})",
                    ))

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        config = self.get_config(ctx)
        min_per = config["params"]["min_per_shift"]

        if config["priority"] == "mandatory":
            for date_str in v.dates:
                for sid in v.shift_type_ids:
                    model.Add(
                        sum(
                            v.shifts[eid][date_str][sid]
                            for eid in v.employee_ids
                            if date_str in v.shifts.get(eid, {})
                        )
                        >= min_per
                    )


class PriorityShiftCoverage(Rule):
    """Higher-priority shifts must be covered before lower-priority ones."""

    id = "priority_shift_coverage"
    name = "Cobertura por prioridad de turno"
    category = "coverage"
    default_priority = "mandatory"
    default_weight = 9
    default_params = {}

    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        config = self.get_config(ctx)
        violations = []
        sorted_shifts = sorted(ctx.shift_types, key=lambda s: s["priority_order"])

        for date_str in _all_dates(ctx.year, ctx.month):
            day_assignments = [
                a for a in ctx.assignments
                if a["date"] == date_str and a["shift_type_id"] is not None
            ]
            covered_ids = {a["shift_type_id"] for a in day_assignments}

            for i, high in enumerate(sorted_shifts):
                if high["id"] in covered_ids:
                    continue

                # Check if a lower-priority shift is covered while this one isn't
                for low in sorted_shifts[i + 1:]:
                    if low["id"] in covered_ids:
                        severity = "grave" if config["priority"] == "mandatory" else "warning"
                        violations.append(Violation(
                            rule_id=self.id,
                            date=date_str,
                            employee_id=None,
                            severity=severity,
                            resolvable=True,
                            message=f"{date_str}: turno {low['name']} (prioridad {low['priority_order']}) cubierto pero {high['name']} (prioridad {high['priority_order']}) sin cubrir",
                        ))
                        break

        return violations

    def add_constraints(
        self, model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
    ) -> None:
        sorted_shifts = sorted(ctx.shift_types, key=lambda s: s["priority_order"])

        for date_str in v.dates:
            for i in range(len(sorted_shifts) - 1):
                high = sorted_shifts[i]
                low = sorted_shifts[i + 1]

                if high["id"] not in v.shift_type_ids or low["id"] not in v.shift_type_ids:
                    continue

                high_covered = sum(
                    v.shifts[eid][date_str][high["id"]]
                    for eid in v.employee_ids
                    if date_str in v.shifts.get(eid, {})
                )
                low_covered = sum(
                    v.shifts[eid][date_str][low["id"]]
                    for eid in v.employee_ids
                    if date_str in v.shifts.get(eid, {})
                )

                # high priority must be >= low priority in coverage
                model.Add(high_covered >= low_covered)


def _find_shift_by_keyword(shift_types: list[dict], keyword: str) -> dict | None:
    """Match shift by name keyword or priority order."""
    keyword_lower = keyword.lower()
    priority_map = {"morning": 1, "afternoon": 2}

    if keyword_lower in priority_map:
        target_priority = priority_map[keyword_lower]
        for st in shift_types:
            if st["priority_order"] == target_priority:
                return st

    for st in shift_types:
        if keyword_lower in st["name"].lower():
            return st

    return None
