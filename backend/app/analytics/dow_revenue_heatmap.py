from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    query = text("""
        SELECT EXTRACT(dow FROM pickup_datetime)::int AS dow,
               EXTRACT(hour FROM pickup_datetime)::int AS hour,
               ROUND(SUM(total_amount)::numeric, 2)::float AS revenue
        FROM trips
        WHERE data_month = :data_month
        GROUP BY dow, hour
        ORDER BY dow, hour
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    return [
        {"dow": row.dow, "dow_label": DOW_LABELS[row.dow], "hour": row.hour, "revenue": row.revenue}
        for row in result.fetchall()
    ]
