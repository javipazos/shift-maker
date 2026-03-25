from collections.abc import Generator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DbConn(Protocol):
    row_factory: Any

    def execute(self, sql: str, parameters: tuple = ...) -> Any: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...


_db_conn: DbConn | None = None


def set_db_conn(conn: DbConn) -> None:
    global _db_conn
    _db_conn = conn


def get_db() -> Generator[DbConn, None, None]:
    assert _db_conn is not None, "Database not initialized"
    yield _db_conn
