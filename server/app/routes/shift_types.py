from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import DbConn, get_db
from app.models import ShiftType, ShiftTypeCreate, ShiftTypeUpdate

router = APIRouter(prefix="/api/shift-types", tags=["shift-types"])


@router.get("", response_model=list[ShiftType])
def list_shift_types(
    status: str = Query("active"),
    db: DbConn = Depends(get_db),
):
    if status == "all":
        rows = db.execute(
            "SELECT * FROM shift_types ORDER BY priority_order"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM shift_types WHERE status = ? ORDER BY priority_order",
            (status,),
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=ShiftType, status_code=201)
def create_shift_type(
    data: ShiftTypeCreate,
    db: DbConn = Depends(get_db),
):
    cursor = db.execute(
        """INSERT INTO shift_types
        (name, start_time, end_time, effective_hours, priority_order, color, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data.name,
            data.start_time,
            data.end_time,
            data.effective_hours,
            data.priority_order,
            data.color,
            data.status.value,
        ),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM shift_types WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(row)


@router.put("/{shift_type_id}", response_model=ShiftType)
def update_shift_type(
    shift_type_id: int,
    data: ShiftTypeUpdate,
    db: DbConn = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM shift_types WHERE id = ?", (shift_type_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Shift type not found")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return dict(existing)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.append(shift_type_id)

    db.execute(
        f"UPDATE shift_types SET {set_clause} WHERE id = ?",
        values,
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM shift_types WHERE id = ?", (shift_type_id,)
    ).fetchone()
    return dict(row)


@router.delete("/{shift_type_id}")
def delete_shift_type(
    shift_type_id: int,
    db: DbConn = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM shift_types WHERE id = ?", (shift_type_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Shift type not found")

    db.execute("DELETE FROM assignments WHERE shift_type_id = ?", (shift_type_id,))
    db.execute("DELETE FROM shift_types WHERE id = ?", (shift_type_id,))
    db.commit()
    return {"ok": True}
