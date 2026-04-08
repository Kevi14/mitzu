from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    query = text("""
        SELECT EXTRACT(hour FROM pickup_datetime)::int AS hour,
               COUNT(*) AS trips
        FROM trips
        WHERE data_month = :data_month
        GROUP BY hour
        ORDER BY hour
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    return [{"hour": row.hour, "trips": row.trips} for row in result.fetchall()]
