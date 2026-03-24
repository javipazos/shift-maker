import json


def test_schema_creates_all_tables(db_conn):
    tables = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t["name"] for t in tables]

    assert "employees" in table_names
    assert "shift_types" in table_names
    assert "absences" in table_names
    assert "rules" in table_names
    assert "schedules" in table_names
    assert "assignments" in table_names


def test_foreign_keys_enabled(db_conn):
    result = db_conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1


def test_seed_inserts_employees(seeded_db):
    employees = seeded_db.execute("SELECT * FROM employees").fetchall()
    assert len(employees) == 4

    ana = employees[0]
    assert ana["name"] == "Ana García"
    assert ana["hours_per_day"] == 7.5
    assert ana["max_hours_per_week"] == 37.5
    assert ana["contract_type"] == "full_time"
    assert ana["status"] == "active"

    pedro = employees[3]
    assert pedro["contract_type"] == "part_time"
    assert pedro["shift_preference"] == "morning"


def test_seed_inserts_shift_types(seeded_db):
    shift_types = seeded_db.execute(
        "SELECT * FROM shift_types ORDER BY priority_order"
    ).fetchall()
    assert len(shift_types) == 3

    morning = shift_types[0]
    assert morning["name"] == "Mañana"
    assert morning["start_time"] == "07:00"
    assert morning["end_time"] == "14:30"
    assert morning["priority_order"] == 1

    afternoon = shift_types[1]
    assert afternoon["name"] == "Tarde"
    assert afternoon["priority_order"] == 2


def test_seed_inserts_all_14_rules(seeded_db):
    rules = seeded_db.execute("SELECT * FROM rules").fetchall()
    assert len(rules) == 14

    rule_ids = {r["id"] for r in rules}
    assert "min_rest_between_shifts" in rule_ids
    assert "max_consecutive_days" in rule_ids
    assert "min_daily_coverage" in rule_ids
    assert "max_weekly_hours" in rule_ids
    assert "requested_days_off" in rule_ids


def test_seed_rule_params_are_valid_json(seeded_db):
    rules = seeded_db.execute("SELECT id, params FROM rules").fetchall()
    for rule in rules:
        params = json.loads(rule["params"])
        assert isinstance(params, dict)


def test_seed_is_idempotent(seeded_db):
    """Running seed twice doesn't duplicate data."""
    from app.db import seed_data

    seed_data(seeded_db)

    employees = seeded_db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    shift_types = seeded_db.execute("SELECT COUNT(*) FROM shift_types").fetchone()[0]
    rules = seeded_db.execute("SELECT COUNT(*) FROM rules").fetchone()[0]

    assert employees == 4
    assert shift_types == 3
    assert rules == 14


def test_schedule_unique_constraint(seeded_db):
    seeded_db.execute(
        "INSERT INTO schedules (month, year) VALUES (?, ?)", (1, 2026)
    )
    seeded_db.commit()

    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        seeded_db.execute(
            "INSERT INTO schedules (month, year) VALUES (?, ?)", (1, 2026)
        )


def test_assignment_unique_constraint(seeded_db):
    seeded_db.execute(
        "INSERT INTO schedules (month, year) VALUES (?, ?)", (1, 2026)
    )
    schedule_id = seeded_db.execute("SELECT last_insert_rowid()").fetchone()[0]

    seeded_db.execute(
        "INSERT INTO assignments (schedule_id, date, employee_id, shift_type_id) VALUES (?, ?, ?, ?)",
        (schedule_id, "2026-01-05", 1, 1),
    )

    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        seeded_db.execute(
            "INSERT INTO assignments (schedule_id, date, employee_id, shift_type_id) VALUES (?, ?, ?, ?)",
            (schedule_id, "2026-01-05", 1, 2),
        )


def test_assignment_allows_null_shift_type(seeded_db):
    seeded_db.execute(
        "INSERT INTO schedules (month, year) VALUES (?, ?)", (1, 2026)
    )
    schedule_id = seeded_db.execute("SELECT last_insert_rowid()").fetchone()[0]

    seeded_db.execute(
        "INSERT INTO assignments (schedule_id, date, employee_id, shift_type_id) VALUES (?, ?, ?, ?)",
        (schedule_id, "2026-01-05", 1, None),
    )
    seeded_db.commit()

    assignment = seeded_db.execute(
        "SELECT * FROM assignments WHERE schedule_id = ?", (schedule_id,)
    ).fetchone()
    assert assignment["shift_type_id"] is None


import pytest
