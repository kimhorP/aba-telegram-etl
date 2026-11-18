from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from src.utils.database import engine
from web import queries

app = FastAPI(title="ABA Transactions Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Summary(BaseModel):
    total_khr: int
    count: int
    avg_khr: float | None
    usd_count: int
    khr_count: int


class TimeseriesPoint(BaseModel):
    period: str
    total_khr: int
    count: int


class BreakdownRow(BaseModel):
    label: str
    total_khr: int
    count: int


class Patterns(BaseModel):
    dow: list[BreakdownRow]
    hour: list[BreakdownRow]


class RecentRow(BaseModel):
    id: int
    date: datetime | None
    shop: str | None
    customer: str | None
    bank: str | None
    currency: str | None
    amount: int | None
    khr: int | None
    remark: str | None


class MovementPeriod(BaseModel):
    current: int | None
    previous: int | None
    delta: int | None
    pct: float | None


class Movement(BaseModel):
    dod: MovementPeriod
    mom: MovementPeriod
    yoy: MovementPeriod


def _run(fn, empty, *args, **kwargs):
    try:
        with engine.connect() as conn:
            return fn(conn, *args, **kwargs)
    except ProgrammingError as exc:
        message = str(exc.orig if hasattr(exc, "orig") else exc)
        if "does not exist" in message:
            return empty()
        raise HTTPException(503, "Database error") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Cannot reach database") from exc


@app.exception_handler(RequestValidationError)
async def invalid_params(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": "Invalid parameters"})


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/shops", response_model=list[str])
def get_shops():
    return _run(queries.shops, lambda: ["All shops"], None, None, None)


@app.get("/api/summary", response_model=Summary)
def get_summary(
    shop: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    empty = lambda: {
        "total_khr": 0,
        "count": 0,
        "avg_khr": None,
        "usd_count": 0,
        "khr_count": 0,
    }
    return _run(queries.summary, empty, shop, start, end)


@app.get("/api/timeseries", response_model=list[TimeseriesPoint])
def get_timeseries(
    bucket: Literal["day", "week", "month", "6month", "year"] = "day",
    shop: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    return _run(queries.timeseries, list, shop, start, end, bucket)


@app.get("/api/breakdown", response_model=list[BreakdownRow])
def get_breakdown(
    dim: Literal["shop_name", "sender_bank", "currency", "customer_name"],
    order: Literal["amount", "count"] = "amount",
    limit: int | None = Query(None, ge=1, le=50),
    shop: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    return _run(queries.breakdown, list, shop, start, end, dim, order, limit)


@app.get("/api/patterns", response_model=Patterns)
def get_patterns(
    shop: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    empty = lambda: {"dow": [], "hour": []}
    return _run(queries.patterns, empty, shop, start, end)


@app.get("/api/recent", response_model=list[RecentRow])
def get_recent(
    limit: int = Query(50, ge=1, le=500),
    shop: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    return _run(queries.recent, list, shop, start, end, limit)


@app.get("/api/movement", response_model=Movement)
def get_movement(
    shop: str | None = None,
    start: date | None = None,
    end: date | None = None,
):
    null = {"current": None, "previous": None, "delta": None, "pct": None}
    empty = lambda: {"dod": null, "mom": null, "yoy": null}
    return _run(queries.movement, empty, shop, start, end)
