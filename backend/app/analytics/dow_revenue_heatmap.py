from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

_SQL = """
    SELECT EXTRACT(dow FROM pickup_datetime)::int AS dow,
           EXTRACT(hour FROM pickup_datetime)::int AS hour,
           ROUND(SUM(total_amount)::numeric, 2)::float AS revenue
    FROM trips
    WHERE data_month = :data_month
    {filters}
    GROUP BY dow, hour
    ORDER BY dow, hour
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    filter_sql, filter_params = build_filter_clause(filters)
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, {"data_month": date(year, month, 1), **filter_params})
    return [
        {"dow": row.dow, "dow_label": DOW_LABELS[row.dow], "hour": row.hour, "revenue": row.revenue}
        for row in result.fetchall()
    ]
