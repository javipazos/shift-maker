import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_db
from app.models import (
    Assignment,
    AssignmentsBulkUpdate,
    Schedule,
    ScheduleStatusUpdate,
)
from app.rules.base import ScheduleContext
from app.services.validator import validate_schedule, compute_score
from app.solver.solver import solve_schedule

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("/{year}/{month}")
def get_schedule(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
):
    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not schedule:
        return {"schedule": None, "assignments": []}

    assignments = db.execute(
        "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ? ORDER BY date, employee_id",
        (schedule["id"],),
    ).fetchall()

    return {
        "schedule": dict(schedule),
        "assignments": [dict(a) for a in assignments],
    }


@router.post("/{year}/{month}", status_code=201)
def create_schedule(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if existing:
        return dict(existing)

    cursor = db.execute(
        "INSERT INTO schedules (year, month) VALUES (?, ?)",
        (year, month),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM schedules WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(row)


@router.put("/{year}/{month}/assignments")
def update_assignments(
    year: int,
    month: int,
    data: AssignmentsBulkUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule_id = schedule["id"]

    db.execute(
        "DELETE FROM assignments WHERE schedule_id = ?", (schedule_id,)
    )

    for a in data.assignments:
        db.execute(
            "INSERT INTO assignments (schedule_id, date, employee_id, shift_type_id) VALUES (?, ?, ?, ?)",
            (schedule_id, a.date, a.employee_id, a.shift_type_id),
        )

    db.execute(
        "UPDATE schedules SET updated_at = datetime('now') WHERE id = ?",
        (schedule_id,),
    )
    db.commit()

    assignments = db.execute(
        "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ? ORDER BY date, employee_id",
        (schedule_id,),
    ).fetchall()

    return {"assignments": [dict(a) for a in assignments]}


@router.put("/{year}/{month}/status")
def update_schedule_status(
    year: int,
    month: int,
    data: ScheduleStatusUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.execute(
        "UPDATE schedules SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (data.status.value, schedule["id"]),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM schedules WHERE id = ?", (schedule["id"],)
    ).fetchone()
    return dict(row)


def _build_schedule_context(
    year: int, month: int, assignments: list[dict], db: sqlite3.Connection
) -> ScheduleContext:
    employees = [
        dict(r) for r in db.execute(
            "SELECT * FROM employees WHERE status = 'active'"
        ).fetchall()
    ]
    shift_types = [
        dict(r) for r in db.execute(
            "SELECT * FROM shift_types WHERE status = 'active'"
        ).fetchall()
    ]
    absences = [
        dict(r) for r in db.execute(
            "SELECT * FROM absences WHERE start_date <= ? AND end_date >= ?",
            (f"{year}-{month:02d}-31", f"{year}-{month:02d}-01"),
        ).fetchall()
    ]
    rules_rows = db.execute("SELECT * FROM rules").fetchall()
    rules_config = {}
    for r in rules_rows:
        rules_config[r["id"]] = {
            "priority": r["priority"],
            "weight": r["weight"],
            "params": json.loads(r["params"]),
            "active": bool(r["active"]),
        }

    return ScheduleContext(
        year=year,
        month=month,
        employees=employees,
        shift_types=shift_types,
        absences=absences,
        assignments=assignments,
        rules_config=rules_config,
    )


@router.post("/{year}/{month}/validate")
def validate(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
):
    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    assignments = [
        dict(a) for a in db.execute(
            "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ?",
            (schedule["id"],),
        ).fetchall()
    ]

    ctx = _build_schedule_context(year, month, assignments, db)
    violations = validate_schedule(ctx)
    score = compute_score(violations)

    correctable = [v for v in violations if v.resolvable]
    structural = [v for v in violations if not v.resolvable]

    return {
        "violations": [
            {
                "rule_id": v.rule_id,
                "date": v.date,
                "employee_id": v.employee_id,
                "severity": v.severity,
                "resolvable": v.resolvable,
                "message": v.message,
            }
            for v in violations
        ],
        "score": score,
        "correctable_count": len(correctable),
        "structural_count": len(structural),
    }


@router.post("/{year}/{month}/generate")
def generate(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
):
    # Ensure schedule exists
    existing = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not existing:
        db.execute(
            "INSERT INTO schedules (year, month) VALUES (?, ?)",
            (year, month),
        )
        db.commit()
        existing = db.execute(
            "SELECT * FROM schedules WHERE year = ? AND month = ?",
            (year, month),
        ).fetchone()

    schedule_id = existing["id"]

    ctx = _build_schedule_context(year, month, [], db)
    result = solve_schedule(ctx)

    if result.assignments:
        db.execute(
            "DELETE FROM assignments WHERE schedule_id = ?", (schedule_id,)
        )
        for a in result.assignments:
            db.execute(
                "INSERT INTO assignments (schedule_id, date, employee_id, shift_type_id) VALUES (?, ?, ?, ?)",
                (schedule_id, a["date"], a["employee_id"], a["shift_type_id"]),
            )
        db.execute(
            "UPDATE schedules SET updated_at = datetime('now') WHERE id = ?",
            (schedule_id,),
        )
        db.commit()

    return {
        "status": result.status,
        "assignments": result.assignments,
        "violations": [
            {
                "rule_id": v.rule_id,
                "date": v.date,
                "employee_id": v.employee_id,
                "severity": v.severity,
                "resolvable": v.resolvable,
                "message": v.message,
            }
            for v in result.violations
        ],
        "score": result.score,
        "solve_time_ms": result.solve_time_ms,
        "relaxed_rules": result.relaxed_rules,
    }


@router.get("/{year}/{month}/summary")
def summary(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
):
    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    employees = [
        dict(r) for r in db.execute(
            "SELECT * FROM employees WHERE status = 'active' ORDER BY id"
        ).fetchall()
    ]
    shift_types = [
        dict(r) for r in db.execute(
            "SELECT * FROM shift_types WHERE status = 'active'"
        ).fetchall()
    ]
    assignments = [
        dict(r) for r in db.execute(
            "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ?",
            (schedule["id"],),
        ).fetchall()
    ]

    shift_map = {st["id"]: st for st in shift_types}

    employee_stats = []
    for emp in employees:
        emp_assignments = [
            a for a in assignments
            if a["employee_id"] == emp["id"] and a["shift_type_id"] is not None
        ]
        total_hours = sum(
            shift_map.get(a["shift_type_id"], {}).get("effective_hours", 0)
            for a in emp_assignments
        )
        days_worked = len(emp_assignments)
        weekly_avg = round(total_hours / 4.3, 1) if total_hours > 0 else 0

        # Max consecutive days
        working_dates = sorted(a["date"] for a in emp_assignments)
        max_consec = _max_consecutive(working_dates)

        # Free weekends
        from app.rules.equity import _get_weekends
        weekends = _get_weekends(year, month)
        free_weekends = 0
        for sat, sun in weekends:
            sat_works = any(
                a["date"] == sat and a["shift_type_id"] is not None
                for a in assignments if a["employee_id"] == emp["id"]
            )
            sun_works = any(
                a["date"] == sun and a["shift_type_id"] is not None
                for a in assignments if a["employee_id"] == emp["id"]
            )
            if not sat_works and not sun_works:
                free_weekends += 1

        employee_stats.append({
            "employee_id": emp["id"],
            "name": emp["name"],
            "days_worked": days_worked,
            "total_hours": round(total_hours, 1),
            "weekly_avg_hours": weekly_avg,
            "max_consecutive_days": max_consec,
            "free_weekends": free_weekends,
        })

    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    coverage_stats = []
    for d in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{d:02d}"
        count = sum(
            1 for a in assignments
            if a["date"] == date_str and a["shift_type_id"] is not None
        )
        coverage_stats.append({"date": date_str, "count": count})

    return {
        "employees": employee_stats,
        "coverage": coverage_stats,
    }


@router.get("/{year}/{month}/previous-context")
def previous_context(
    year: int,
    month: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return last 7 days of the previous month's schedule for continuity."""
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (prev_year, prev_month),
    ).fetchone()

    if not schedule:
        return {"assignments": [], "prev_year": prev_year, "prev_month": prev_month}

    import calendar
    days_in_prev = calendar.monthrange(prev_year, prev_month)[1]
    start_day = max(1, days_in_prev - 6)
    start_date = f"{prev_year}-{prev_month:02d}-{start_day:02d}"

    assignments = [
        dict(r) for r in db.execute(
            "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ? AND date >= ? ORDER BY date, employee_id",
            (schedule["id"], start_date),
        ).fetchall()
    ]

    return {
        "assignments": assignments,
        "prev_year": prev_year,
        "prev_month": prev_month,
    }


def _max_consecutive(sorted_dates: list[str]) -> int:
    if not sorted_dates:
        return 0

    from app.rules.rest import _next_date

    max_streak = 1
    current = 1

    for i in range(1, len(sorted_dates)):
        if _next_date(sorted_dates[i - 1]) == sorted_dates[i]:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 1

    return max_streak
