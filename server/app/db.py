from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.deps import DbConn

DB_PATH = Path(__file__).parent.parent / "shift_maker.db"

TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        hours_per_day REAL NOT NULL DEFAULT 7.5,
        max_hours_per_week REAL NOT NULL DEFAULT 37.5,
        contract_type TEXT NOT NULL DEFAULT 'full_time',
        shift_preference TEXT NOT NULL DEFAULT 'none',
        preference_strength TEXT NOT NULL DEFAULT 'desirable',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS shift_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        effective_hours REAL NOT NULL,
        priority_order INTEGER NOT NULL,
        color TEXT NOT NULL DEFAULT '#4A90D9',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        type TEXT NOT NULL,
        counts_as_work INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS rules (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'mandatory',
        weight INTEGER NOT NULL DEFAULT 5,
        params TEXT NOT NULL DEFAULT '{}',
        active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(month, year)
    )""",
    """CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        shift_type_id INTEGER REFERENCES shift_types(id),
        UNIQUE(schedule_id, date, employee_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_assignments_schedule ON assignments(schedule_id)",
    "CREATE INDEX IF NOT EXISTS idx_absences_employee ON absences(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_absences_dates ON absences(start_date, end_date)",
]

SEED_RULES = [
    {
        "id": "min_rest_between_shifts",
        "name": "Descanso mínimo entre jornadas",
        "category": "rest",
        "priority": "mandatory",
        "weight": 10,
        "params": {"min_hours": 12},
    },
    {
        "id": "max_consecutive_days",
        "name": "Máximo días consecutivos trabajados",
        "category": "rest",
        "priority": "mandatory",
        "weight": 9,
        "params": {"max_days": 6},
    },
    {
        "id": "min_consecutive_free_days",
        "name": "Días libres consecutivos mínimos",
        "category": "rest",
        "priority": "desirable",
        "weight": 6,
        "params": {"min_days": 2},
    },
    {
        "id": "weekly_rest",
        "name": "Descanso semanal mínimo",
        "category": "rest",
        "priority": "mandatory",
        "weight": 8,
        "params": {"min_days": 1.5},
    },
    {
        "id": "min_daily_coverage",
        "name": "Cobertura mínima por día",
        "category": "coverage",
        "priority": "mandatory",
        "weight": 10,
        "params": {"weekday_min": 2, "weekend_min": 2},
    },
    {
        "id": "weekend_shift_coverage",
        "name": "Cobertura por turno en fin de semana",
        "category": "coverage",
        "priority": "mandatory",
        "weight": 8,
        "params": {"required_shifts": ["morning", "afternoon"]},
    },
    {
        "id": "min_per_shift_coverage",
        "name": "Cobertura mínima por turno",
        "category": "coverage",
        "priority": "desirable",
        "weight": 5,
        "params": {"min_per_shift": 1},
        "active": False,
    },
    {
        "id": "priority_shift_coverage",
        "name": "Cobertura por prioridad de turno",
        "category": "coverage",
        "priority": "mandatory",
        "weight": 9,
        "params": {},
    },
    {
        "id": "monthly_free_weekend",
        "name": "Fin de semana libre mensual",
        "category": "equity",
        "priority": "desirable",
        "weight": 7,
        "params": {"min_free_weekends": 1},
    },
    {
        "id": "weekend_distribution",
        "name": "Distribución equitativa de fines de semana",
        "category": "equity",
        "priority": "desirable",
        "weight": 6,
        "params": {},
    },
    {
        "id": "hours_distribution",
        "name": "Distribución equitativa de horas",
        "category": "equity",
        "priority": "desirable",
        "weight": 6,
        "params": {},
    },
    {
        "id": "max_weekly_hours",
        "name": "Horas máximas semanales",
        "category": "limits",
        "priority": "mandatory",
        "weight": 9,
        "params": {},
    },
    {
        "id": "max_daily_hours",
        "name": "Horas máximas diarias",
        "category": "limits",
        "priority": "mandatory",
        "weight": 8,
        "params": {"max_hours": 9},
    },
    {
        "id": "requested_days_off",
        "name": "Días libres pedidos",
        "category": "limits",
        "priority": "mandatory",
        "weight": 10,
        "params": {},
    },
]

SEED_EMPLOYEES = [
    {"name": "Ana García", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"name": "Carlos López", "hours_per_day": 7.5, "max_hours_per_week": 37.5},
    {"name": "María Fernández", "hours_per_day": 8.0, "max_hours_per_week": 40.0},
    {
        "name": "Pedro Martín",
        "hours_per_day": 4.0,
        "max_hours_per_week": 20.0,
        "contract_type": "part_time",
        "shift_preference": "morning",
        "preference_strength": "desirable",
    },
]

SEED_SHIFT_TYPES = [
    {
        "name": "Mañana",
        "start_time": "07:00",
        "end_time": "14:30",
        "effective_hours": 7.5,
        "priority_order": 1,
        "color": "#4A90D9",
    },
    {
        "name": "Tarde",
        "start_time": "14:30",
        "end_time": "22:00",
        "effective_hours": 7.5,
        "priority_order": 2,
        "color": "#E8A838",
    },
    {
        "name": "Media mañana",
        "start_time": "09:00",
        "end_time": "13:00",
        "effective_hours": 4.0,
        "priority_order": 3,
        "color": "#7EC87E",
    },
]


def _dict_factory(cursor: Any, row: tuple) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_connection(db_path: Path = DB_PATH) -> DbConn:
    if TURSO_URL:
        import libsql_experimental as libsql  # type: ignore[import-untyped]
        conn = libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN or "")
        conn.row_factory = _dict_factory
        return conn

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn: DbConn) -> None:
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(stmt)
    conn.commit()


def seed_data(conn: DbConn) -> None:
    _seed_rules(conn)
    _seed_employees(conn)
    _seed_shift_types(conn)
    conn.commit()


def _seed_rules(conn: DbConn) -> None:
    for rule in SEED_RULES:
        active = 1 if rule.get("active", True) else 0
        conn.execute(
            """INSERT OR IGNORE INTO rules (id, name, category, priority, weight, params, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                rule["id"],
                rule["name"],
                rule["category"],
                rule["priority"],
                rule["weight"],
                json.dumps(rule["params"]),
                active,
            ),
        )


def _seed_employees(conn: DbConn) -> None:
    existing = conn.execute("SELECT COUNT(*) as cnt FROM employees").fetchone()
    count = existing["cnt"] if isinstance(existing, dict) else existing[0]
    if count > 0:
        return

    for emp in SEED_EMPLOYEES:
        conn.execute(
            """INSERT INTO employees
            (name, hours_per_day, max_hours_per_week, contract_type, shift_preference, preference_strength)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                emp["name"],
                emp["hours_per_day"],
                emp["max_hours_per_week"],
                emp.get("contract_type", "full_time"),
                emp.get("shift_preference", "none"),
                emp.get("preference_strength", "desirable"),
            ),
        )


def _seed_shift_types(conn: DbConn) -> None:
    existing = conn.execute("SELECT COUNT(*) as cnt FROM shift_types").fetchone()
    count = existing["cnt"] if isinstance(existing, dict) else existing[0]
    if count > 0:
        return

    for st in SEED_SHIFT_TYPES:
        conn.execute(
            """INSERT INTO shift_types
            (name, start_time, end_time, effective_hours, priority_order, color)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                st["name"],
                st["start_time"],
                st["end_time"],
                st["effective_hours"],
                st["priority_order"],
                st["color"],
            ),
        )


def init_db(db_path: Path = DB_PATH) -> DbConn:
    conn = get_connection(db_path)
    create_schema(conn)
    seed_data(conn)
    return conn
