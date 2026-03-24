import sqlite3
from collections.abc import Generator

_db_conn: sqlite3.Connection | None = None


def set_db_conn(conn: sqlite3.Connection) -> None:
    global _db_conn
    _db_conn = conn


def get_db() -> Generator[sqlite3.Connection]:
    assert _db_conn is not None, "Database not initialized"
    yield _db_conn
