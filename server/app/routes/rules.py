import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_db
from app.models import Rule, RuleUpdate

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _row_to_rule(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["params"] = json.loads(d["params"])
    d["active"] = bool(d["active"])
    return d


@router.get("", response_model=list[Rule])
def list_rules(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM rules ORDER BY category, id").fetchall()
    return [_row_to_rule(row) for row in rows]


@router.put("/{rule_id}", response_model=Rule)
def update_rule(
    rule_id: str,
    data: RuleUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM rules WHERE id = ?", (rule_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return _row_to_rule(existing)

    if "params" in updates:
        updates["params"] = json.dumps(updates["params"])
    if "active" in updates:
        updates["active"] = int(updates["active"])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = [v.value if hasattr(v, "value") else v for v in updates.values()]
    values.append(rule_id)

    db.execute(f"UPDATE rules SET {set_clause} WHERE id = ?", values)
    db.commit()

    row = db.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    return _row_to_rule(row)
