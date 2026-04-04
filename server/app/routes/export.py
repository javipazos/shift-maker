from unicodedata import normalize

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.deps import DbConn, get_db
from app.services.exporter import export_ics, export_schedule

router = APIRouter(prefix="/api/schedules", tags=["export"])


@router.get("/{year}/{month}/export")
def export(
    year: int,
    month: int,
    db: DbConn = Depends(get_db),
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
            "SELECT * FROM shift_types WHERE status = 'active' ORDER BY priority_order"
        ).fetchall()
    ]
    assignments = [
        dict(r) for r in db.execute(
            "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ?",
            (schedule["id"],),
        ).fetchall()
    ]

    output = export_schedule(year, month, employees, shift_types, assignments)
    filename = f"horario_{year}_{month:02d}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _sanitize_filename(name: str) -> str:
    normalized = normalize("NFD", name)
    safe = "".join(c for c in normalized if c.isalnum() or c in " _-")
    return safe.strip().replace(" ", "_")


@router.get("/{year}/{month}/export-ics/{employee_id}")
def export_ics_route(
    year: int,
    month: int,
    employee_id: int,
    db: DbConn = Depends(get_db),
):
    schedule = db.execute(
        "SELECT * FROM schedules WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    employee = db.execute(
        "SELECT * FROM employees WHERE id = ?", (employee_id,)
    ).fetchone()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    shift_types = [
        dict(r) for r in db.execute(
            "SELECT * FROM shift_types WHERE status = 'active' ORDER BY priority_order"
        ).fetchall()
    ]
    assignments = [
        dict(r) for r in db.execute(
            "SELECT date, employee_id, shift_type_id FROM assignments WHERE schedule_id = ?",
            (schedule["id"],),
        ).fetchall()
    ]

    ics_content = export_ics(dict(employee), shift_types, assignments)
    safe_name = _sanitize_filename(employee["name"])
    filename = f"{safe_name}_{year}-{month:02d}.ics"

    return PlainTextResponse(
        ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
