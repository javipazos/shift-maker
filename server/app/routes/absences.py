from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import DbConn, get_db
from app.models import Absence, AbsenceCreate, AbsenceUpdate

router = APIRouter(prefix="/api/absences", tags=["absences"])


@router.get("", response_model=list[Absence])
def list_absences(
    year: int | None = Query(None),
    month: int | None = Query(None),
    employee_id: int | None = Query(None),
    db: DbConn = Depends(get_db),
):
    query = "SELECT * FROM absences WHERE 1=1"
    params: list = []

    if year and month:
        month_start = f"{year}-{month:02d}-01"
        month_end = f"{year}-{month:02d}-31"
        query += " AND start_date <= ? AND end_date >= ?"
        params.extend([month_end, month_start])

    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)

    query += " ORDER BY start_date"
    rows = db.execute(query, params).fetchall()
    return [_row_to_absence(r) for r in rows]


@router.post("", response_model=Absence, status_code=201)
def create_absence(
    data: AbsenceCreate,
    db: DbConn = Depends(get_db),
):
    employee = db.execute(
        "SELECT id FROM employees WHERE id = ?", (data.employee_id,)
    ).fetchone()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    cursor = db.execute(
        """INSERT INTO absences
        (employee_id, start_date, end_date, type, counts_as_work, notes)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            data.employee_id,
            data.start_date,
            data.end_date,
            data.type.value,
            int(data.counts_as_work),
            data.notes,
        ),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM absences WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_absence(row)


@router.put("/{absence_id}", response_model=Absence)
def update_absence(
    absence_id: int,
    data: AbsenceUpdate,
    db: DbConn = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM absences WHERE id = ?", (absence_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Absence not found")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return _row_to_absence(existing)

    if "type" in updates:
        updates["type"] = updates["type"].value
    if "counts_as_work" in updates:
        updates["counts_as_work"] = int(updates["counts_as_work"])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())
    values.append(absence_id)

    db.execute(f"UPDATE absences SET {set_clause} WHERE id = ?", values)
    db.commit()

    row = db.execute(
        "SELECT * FROM absences WHERE id = ?", (absence_id,)
    ).fetchone()
    return _row_to_absence(row)


@router.delete("/{absence_id}")
def delete_absence(
    absence_id: int,
    db: DbConn = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM absences WHERE id = ?", (absence_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Absence not found")

    db.execute("DELETE FROM absences WHERE id = ?", (absence_id,))
    db.commit()
    return {"ok": True}


def _row_to_absence(row: Mapping) -> dict:
    d = dict(row)
    d["counts_as_work"] = bool(d["counts_as_work"])
    return d
