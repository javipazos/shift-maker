import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import create_schema, seed_data
from app.deps import get_db
from app.main import app

TEST_DB_PATH = Path(__file__).parent / "test.db"


@pytest.fixture
def db_conn():
    """Fresh in-memory database for each test."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def seeded_db(db_conn):
    """Database with seed data."""
    seed_data(db_conn)
    return db_conn


@pytest.fixture
def client(seeded_db):
    """FastAPI test client with seeded database."""

    def override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
