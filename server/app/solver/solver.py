import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.rules.base import ScheduleContext, SolverVars, Violation
from app.rules.registry import get_all_rules
from app.services.validator import validate_schedule


@dataclass
class SolveResult:
    status: str
    assignments: list[dict]
    violations: list[Violation]
    score: float
    solve_time_ms: float
    relaxed_rules: list[str]


def solve_schedule(
    ctx: ScheduleContext, fixed: list[dict] | None = None
) -> SolveResult:
    start = time.monotonic()

    model = cp_model.CpModel()
    solver_vars = _build_variables(model, ctx)
    _add_basic_constraints(model, solver_vars, ctx)
    _add_fixed_constraints(model, solver_vars, _drop_fixed_on_absent_days(fixed or [], ctx))
    _add_rule_constraints(model, solver_vars, ctx)
    _add_objective(model, solver_vars, ctx)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)
    elapsed_ms = (time.monotonic() - start) * 1000

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments = _extract_assignments(solver, solver_vars, ctx)
        solve_ctx = ScheduleContext(
            year=ctx.year,
            month=ctx.month,
            employees=ctx.employees,
            shift_types=ctx.shift_types,
            absences=ctx.absences,
            assignments=assignments,
            rules_config=ctx.rules_config,
            prev_assignments=ctx.prev_assignments,
        )
        violations = validate_schedule(solve_ctx)
        score = _compute_score(violations)

        return SolveResult(
            status="optimal" if status == cp_model.OPTIMAL else "feasible",
            assignments=assignments,
            violations=violations,
            score=score,
            solve_time_ms=round(elapsed_ms, 1),
            relaxed_rules=_collect_relaxed_rules(solver, solver_vars),
        )

    return SolveResult(
        status="infeasible",
        assignments=[],
        violations=[],
        score=0.0,
        solve_time_ms=round(elapsed_ms, 1),
        relaxed_rules=[],
    )


def _build_variables(
    model: cp_model.CpModel, ctx: ScheduleContext
) -> SolverVars:
    from app.rules.rest import _all_dates, _is_weekend

    current_dates = _all_dates(ctx.year, ctx.month)
    emp_ids = [e["id"] for e in ctx.employees]
    shift_ids = [st["id"] for st in ctx.shift_types]

    prev_dates = sorted({a["date"] for a in ctx.prev_assignments})
    all_dates = prev_dates + current_dates
    prev_date_set = set(prev_dates)

    prev_lookup: dict[tuple[int, str], int | None] = {}
    for a in ctx.prev_assignments:
        prev_lookup[(a["employee_id"], a["date"])] = a["shift_type_id"]

    absent_set = _build_absent_set(ctx)

    shifts: dict[int, dict[str, dict[int, cp_model.IntVar]]] = {}
    works: dict[int, dict[str, cp_model.IntVar]] = {}

    for emp_id in emp_ids:
        shifts[emp_id] = {}
        works[emp_id] = {}

        for date in all_dates:
            shifts[emp_id][date] = {}

            if date in prev_date_set:
                prev_sid = prev_lookup.get((emp_id, date))
                for sid in shift_ids:
                    shifts[emp_id][date][sid] = model.NewConstant(
                        1 if prev_sid == sid else 0
                    )
                works[emp_id][date] = model.NewConstant(
                    1 if prev_sid is not None else 0
                )
            elif (emp_id, date) in absent_set:
                for sid in shift_ids:
                    shifts[emp_id][date][sid] = model.NewConstant(0)
                works[emp_id][date] = model.NewConstant(0)
            else:
                for sid in shift_ids:
                    shifts[emp_id][date][sid] = model.NewBoolVar(
                        f"x_{emp_id}_{date}_{sid}"
                    )
                works[emp_id][date] = model.NewBoolVar(f"w_{emp_id}_{date}")

    return SolverVars(
        shifts=shifts,
        works=works,
        dates=current_dates,
        employee_ids=emp_ids,
        shift_type_ids=shift_ids,
        context_dates=all_dates,
    )


def _add_basic_constraints(
    model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
) -> None:
    absent_set = _build_absent_set(ctx)

    for emp_id in v.employee_ids:
        for date in v.dates:
            if (emp_id, date) in absent_set:
                continue

            model.Add(
                sum(v.shifts[emp_id][date][sid] for sid in v.shift_type_ids) <= 1
            )

            model.Add(
                sum(v.shifts[emp_id][date][sid] for sid in v.shift_type_ids)
                == v.works[emp_id][date]
            )


def _drop_fixed_on_absent_days(
    fixed: list[dict], ctx: ScheduleContext
) -> list[dict]:
    # Pinning a shift where there is an absence would force constant 0 == 1
    # and make the whole model infeasible — the absence wins.
    absent_set = _build_absent_set(ctx)
    return [
        f for f in fixed if (f["employee_id"], f["date"]) not in absent_set
    ]


def _add_fixed_constraints(
    model: cp_model.CpModel, v: SolverVars, fixed: list[dict]
) -> None:
    for f in fixed:
        emp_id = f["employee_id"]
        date = f["date"]
        sid = f["shift_type_id"]

        if emp_id not in v.works or date not in v.works.get(emp_id, {}):
            continue

        if sid is None:
            model.Add(v.works[emp_id][date] == 0)
        elif sid in v.shifts.get(emp_id, {}).get(date, {}):
            model.Add(v.shifts[emp_id][date][sid] == 1)


def _add_rule_constraints(
    model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
) -> None:
    for rule in get_all_rules():
        config = rule.get_config(ctx)
        if not config["active"]:
            continue
        rule.add_constraints(model, v, ctx)


def _add_objective(
    model: cp_model.CpModel, v: SolverVars, ctx: ScheduleContext
) -> None:
    num_dates = len(v.dates)

    total_works_per_emp: dict[int, cp_model.LinearExpr] = {}
    for emp_id in v.employee_ids:
        total_works_per_emp[emp_id] = sum(
            v.works[emp_id][d] for d in v.dates
        )

    max_work = model.NewIntVar(0, num_dates, "max_work")
    min_work = model.NewIntVar(0, num_dates, "min_work")

    for emp_id in v.employee_ids:
        model.Add(max_work >= total_works_per_emp[emp_id])
        model.Add(min_work <= total_works_per_emp[emp_id])

    spread = model.NewIntVar(0, num_dates, "work_spread")
    model.Add(spread == max_work - min_work)

    total_all = sum(total_works_per_emp[eid] for eid in v.employee_ids)

    # Primary: maximize total work days (weight = num_dates + 1 so one extra
    # work day always beats any spread reduction)
    # Relaxing a desirable rule costs its weight in work-day units, so a
    # weight-7 rule is only sacrificed to gain more than 7 work days
    # Secondary: minimize spread between employees
    penalties = sum(_penalty_terms(v, ctx))
    model.Minimize(-total_all * (num_dates + 1) + spread + penalties)


def _penalty_terms(v: SolverVars, ctx: ScheduleContext) -> list:
    from app.rules.registry import get_rule

    one_work_day = len(v.dates) + 1
    terms = []
    for rule_id, violations in v.penalties.items():
        rule = get_rule(rule_id)
        weight = rule.get_config(ctx)["weight"] if rule else 1
        terms.extend(var * weight * one_work_day for var in violations)
    return terms


def _collect_relaxed_rules(solver: cp_model.CpSolver, v: SolverVars) -> list[str]:
    return sorted(
        rule_id
        for rule_id, violations in v.penalties.items()
        if any(solver.Value(var) == 1 for var in violations)
    )


def _extract_assignments(
    solver: cp_model.CpSolver, v: SolverVars, ctx: ScheduleContext
) -> list[dict]:
    assignments = []
    absent_set = _build_absent_set(ctx)

    for emp_id in v.employee_ids:
        for date in v.dates:
            if (emp_id, date) in absent_set:
                continue

            assigned_shift = None
            for sid in v.shift_type_ids:
                if solver.Value(v.shifts[emp_id][date][sid]) == 1:
                    assigned_shift = sid
                    break

            assignments.append({
                "date": date,
                "employee_id": emp_id,
                "shift_type_id": assigned_shift,
            })

    return assignments


def _build_absent_set(ctx: ScheduleContext) -> set[tuple[int, str]]:
    from app.rules.rest import _all_dates

    absent = set()
    all_dates = _all_dates(ctx.year, ctx.month)

    for absence in ctx.absences:
        for d in all_dates:
            if absence["start_date"] <= d <= absence["end_date"]:
                absent.add((absence["employee_id"], d))

    return absent


def _compute_score(violations: list[Violation]) -> float:
    from app.services.validator import compute_score

    return compute_score(violations)
