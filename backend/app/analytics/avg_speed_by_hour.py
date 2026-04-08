from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    SELECT EXTRACT(hour FROM pickup_datetime)::int AS hour,
           ROUND(
               AVG(
                   trip_distance::float /
                   NULLIF(EXTRACT(epoch FROM (dropoff_datetime - pickup_datetime)) / 3600.0, 0)
               )::numeric, 2
           )::float AS avg_mph,
           COUNT(*) AS trips
    FROM trips
    WHERE data_month = :data_month
      AND trip_distance > 0.1
      AND dropoff_datetime > pickup_datetime
      AND EXTRACT(epoch FROM (dropoff_datetime - pickup_datetime)) > 60
      {filters}
    GROUP BY hour
    ORDER BY hour
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    filter_sql, filter_params = build_filter_clause(filters)
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, {"data_month": date(year, month, 1), **filter_params})
    return [{"hour": row.hour, "avg_mph": row.avg_mph, "trips": row.trips} for row in result.fetchall()]
