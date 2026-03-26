import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import verify_token
from app.db import DB_PATH, init_db
from app.deps import get_db, set_db_conn
from app.routes import absences, employees, export, shift_types, rules, schedules

AUTH_ENABLED = bool(os.environ.get("CLERK_JWKS_URL"))
auth_deps = [Depends(verify_token)] if AUTH_ENABLED else []


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

cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(absences.router, dependencies=auth_deps)
app.include_router(employees.router, dependencies=auth_deps)
app.include_router(shift_types.router, dependencies=auth_deps)
app.include_router(rules.router, dependencies=auth_deps)
app.include_router(schedules.router, dependencies=auth_deps)
app.include_router(export.router, dependencies=auth_deps)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
