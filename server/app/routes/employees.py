from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import DbConn, get_db
from app.models import Employee, EmployeeCreate, EmployeeUpdate

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[Employee])
def list_employees(
    status: str = Query("active"),
    db: DbConn = Depends(get_db),
):
    if status == "all":
        rows = db.execute("SELECT * FROM employees ORDER BY id").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM employees WHERE status = ? ORDER BY id", (status,)
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=Employee, status_code=201)
def create_employee(
    data: EmployeeCreate,
    db: DbConn = Depends(get_db),
):
    cursor = db.execute(
        """INSERT INTO employees
        (name, hours_per_day, max_hours_per_week, contract_type,
         shift_preference, preference_strength, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data.name,
            data.hours_per_day,
            data.max_hours_per_week,
            data.contract_type.value,
            data.shift_preference.value,
            data.preference_strength.value,
            data.status.value,
        ),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM employees WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return dict(row)


@router.put("/{employee_id}", response_model=Employee)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: DbConn = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM employees WHERE id = ?", (employee_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return dict(existing)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.append(employee_id)

    db.execute(
        f"UPDATE employees SET {set_clause} WHERE id = ?",
        values,
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM employees WHERE id = ?", (employee_id,)
    ).fetchone()
    return dict(row)


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: DbConn = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM employees WHERE id = ?", (employee_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.execute("DELETE FROM assignments WHERE employee_id = ?", (employee_id,))
    db.execute("DELETE FROM absences WHERE employee_id = ?", (employee_id,))
    db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    db.commit()
    return {"ok": True}
