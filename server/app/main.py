from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import DB_PATH, init_db
from app.deps import get_db, set_db_conn
from app.routes import absences, employees, export, shift_types, rules, schedules


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = init_db(DB_PATH)
    set_db_conn(conn)
    yield
    conn.close()


app = FastAPI(
    title="Shift Maker",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(absences.router)
app.include_router(employees.router)
app.include_router(shift_types.router)
app.include_router(rules.router)
app.include_router(schedules.router)
app.include_router(export.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
