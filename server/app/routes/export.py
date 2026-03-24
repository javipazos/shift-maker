import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.deps import get_db
from app.services.exporter import export_schedule

router = APIRouter(prefix="/api/schedules", tags=["export"])


@router.get("/{year}/{month}/export")
def export(
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
