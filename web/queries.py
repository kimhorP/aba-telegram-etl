from calendar import monthrange
from datetime import date, datetime, time, timedelta

from sqlalchemy import Date, case, cast, func, select

from src.models.transaction import Transaction as T

DIMENSIONS = {
    "shop_name": T.shop_name,
    "sender_bank": T.sender_bank,
    "currency": T.currency,
    "customer_name": T.customer_name,
}


def _conds(shop: str | None, start: date | None, end: date | None) -> list:
    conds = []
    if shop:
        conds.append(T.shop_name == shop)
    if start:
        conds.append(T.date_of_transaction >= datetime.combine(start, time.min))
    if end:
        conds.append(
            T.date_of_transaction
            < datetime.combine(end + timedelta(days=1), time.min)
        )
    return conds


def shops(conn, shop, start, end) -> list[str]:
    stmt = (
        select(T.shop_name)
        .where(T.shop_name.isnot(None), *_conds(shop, start, end))
        .distinct()
        .order_by(T.shop_name)
    )
    return ["All shops", *[row[0] for row in conn.execute(stmt)]]


def summary(conn, shop, start, end) -> dict:
    stmt = select(
        func.coalesce(func.sum(T.formatted_amount), 0).label("total_khr"),
        func.count(T.id).label("count"),
        func.avg(T.formatted_amount).label("avg_khr"),
        func.coalesce(
            func.sum(case((T.currency == "USD", 1), else_=0)), 0
        ).label("usd_count"),
        func.coalesce(
            func.sum(case((T.currency == "KHR", 1), else_=0)), 0
        ).label("khr_count"),
    ).where(*_conds(shop, start, end))
    row = conn.execute(stmt).one()
    return {
        "total_khr": int(row.total_khr),
        "count": row.count,
        "avg_khr": float(row.avg_khr) if row.avg_khr is not None else None,
        "usd_count": int(row.usd_count),
        "khr_count": int(row.khr_count),
    }


def _timeseries_6month(conn, shop, start, end) -> list[dict]:
    month_period = func.date_trunc("month", T.date_of_transaction)
    stmt = (
        select(
            month_period.label("period"),
            func.coalesce(func.sum(T.formatted_amount), 0).label("total_khr"),
            func.count(T.id).label("count"),
        )
        .where(*_conds(shop, start, end))
        .group_by(month_period)
        .order_by(month_period)
    )
    buckets: dict[date, dict] = {}
    for row in conn.execute(stmt):
        m = row.period.date() if isinstance(row.period, datetime) else row.period
        key = date(m.year, m.month if m.month <= 6 else 7, 1)
        b = buckets.setdefault(key, {"total_khr": 0, "count": 0})
        b["total_khr"] += int(row.total_khr)
        b["count"] += row.count
    return [
        {"period": key.isoformat(), "total_khr": v["total_khr"], "count": v["count"]}
        for key, v in sorted(buckets.items())
    ]


def timeseries(conn, shop, start, end, bucket: str) -> list[dict]:
    if bucket == "6month":
        return _timeseries_6month(conn, shop, start, end)
    if bucket == "week":
        period = func.date_trunc("week", T.date_of_transaction)
    elif bucket == "month":
        period = func.date_trunc("month", T.date_of_transaction)
    elif bucket == "year":
        period = func.date_trunc("year", T.date_of_transaction)
    else:
        period = func.cast(T.date_of_transaction, Date)
    stmt = (
        select(
            period.label("period"),
            func.coalesce(func.sum(T.formatted_amount), 0).label("total_khr"),
            func.count(T.id).label("count"),
        )
        .where(*_conds(shop, start, end))
        .group_by(period)
        .order_by(period)
    )
    out = []
    for row in conn.execute(stmt):
        value = row.period
        if isinstance(value, datetime):
            value = value.date()
        out.append(
            {"period": value.isoformat(), "total_khr": int(row.total_khr), "count": row.count}
        )
    return out


def breakdown(
    conn,
    shop,
    start,
    end,
    dim: str,
    order: str = "amount",
    limit: int | None = None,
) -> list[dict]:
    col = DIMENSIONS[dim]
    total_expr = func.coalesce(func.sum(T.formatted_amount), 0).label("total_khr")
    count_expr = func.count(T.id).label("count")
    order_expr = count_expr if order == "count" else total_expr
    stmt = (
        select(col.label("label"), total_expr, count_expr)
        .where(*_conds(shop, start, end), col.isnot(None))
        .group_by(col)
        .order_by(order_expr.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return [
        {"label": row.label, "total_khr": int(row.total_khr), "count": row.count}
        for row in conn.execute(stmt)
    ]


DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def patterns(conn, shop, start, end) -> dict:
    conds = [*_conds(shop, start, end), T.date_of_transaction.isnot(None)]

    dow_expr = func.extract("dow", T.date_of_transaction)
    hour_expr = func.extract("hour", T.date_of_transaction)

    dow_rows = conn.execute(
        select(
            dow_expr.label("d"),
            func.coalesce(func.sum(T.formatted_amount), 0).label("total_khr"),
            func.count(T.id).label("count"),
        )
        .where(*conds)
        .group_by(dow_expr)
    ).all()
    hour_rows = conn.execute(
        select(
            hour_expr.label("h"),
            func.coalesce(func.sum(T.formatted_amount), 0).label("total_khr"),
            func.count(T.id).label("count"),
        )
        .where(*conds)
        .group_by(hour_expr)
    ).all()

    dow_map = {int(r.d): (int(r.total_khr), int(r.count)) for r in dow_rows}
    hour_map = {int(r.h): (int(r.total_khr), int(r.count)) for r in hour_rows}

    dow = [
        {
            "label": DOW_NAMES[d],
            "total_khr": dow_map.get(d, (0, 0))[0],
            "count": dow_map.get(d, (0, 0))[1],
        }
        for d in (1, 2, 3, 4, 5, 6, 0)
    ]
    hour = [
        {
            "label": f"{h:02d}",
            "total_khr": hour_map.get(h, (0, 0))[0],
            "count": hour_map.get(h, (0, 0))[1],
        }
        for h in range(24)
    ]
    return {"dow": dow, "hour": hour}


def recent(conn, shop, start, end, limit: int) -> list[dict]:
    stmt = (
        select(
            T.id,
            T.date_of_transaction,
            T.shop_name,
            T.customer_name,
            T.sender_bank,
            T.currency,
            T.amount,
            T.formatted_amount,
            T.remark,
        )
        .where(*_conds(shop, start, end))
        .order_by(T.date_of_transaction.desc().nullslast(), T.id.desc())
        .limit(limit)
    )
    return [
        {
            "id": row.id,
            "date": row.date_of_transaction.isoformat() if row.date_of_transaction else None,
            "shop": row.shop_name,
            "customer": row.customer_name,
            "bank": row.sender_bank,
            "currency": row.currency,
            "amount": row.amount,
            "khr": row.formatted_amount,
            "remark": row.remark,
        }
        for row in conn.execute(stmt)
    ]


def _period_sum(conn, first: date, last: date, shop: str | None) -> tuple[int, int]:
    stmt = select(
        func.count(T.id),
        func.coalesce(func.sum(T.formatted_amount), 0),
    ).where(
        T.date_of_transaction >= datetime.combine(first, time.min),
        T.date_of_transaction < datetime.combine(last + timedelta(days=1), time.min),
        *([T.shop_name == shop] if shop else []),
    )
    count, total = conn.execute(stmt).one()
    return int(total), count


def _delta(current: int, previous: int | None) -> dict:
    if previous is None:
        return {"current": current, "previous": None, "delta": None, "pct": None}
    delta = current - previous
    pct = round(delta / previous * 100, 1) if previous else None
    return {"current": current, "previous": previous, "delta": delta, "pct": pct}


def _same_day_last_month(d: date) -> date:
    year, month = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def _same_day_last_year(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return date(d.year - 1, 2, 28)


def movement(conn, shop, start, end) -> dict:
    anchor = end
    if anchor is None:
        stmt = select(func.max(T.date_of_transaction)).where(
            *_conds(shop, start, None)
        )
        max_dt = conn.execute(stmt).scalar()
        anchor = max_dt.date() if max_dt else None

    if anchor is None:
        null = {"current": None, "previous": None, "delta": None, "pct": None}
        return {"dod": null, "mom": null, "yoy": null}

    curr_total, curr_count = _period_sum(conn, anchor, anchor, shop)
    current = curr_total if curr_count else 0

    def day_total(day: date) -> int | None:
        total, count = _period_sum(conn, day, day, shop)
        return total if count else None

    return {
        "dod": _delta(current, day_total(anchor - timedelta(days=1))),
        "mom": _delta(current, day_total(_same_day_last_month(anchor))),
        "yoy": _delta(current, day_total(_same_day_last_year(anchor))),
    }
