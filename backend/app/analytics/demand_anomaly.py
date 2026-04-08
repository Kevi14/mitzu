from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    WITH hourly AS (
        SELECT EXTRACT(hour FROM pickup_datetime)::int AS hour,
               COUNT(*) AS trips
        FROM trips
        WHERE data_month = :data_month
        {filters}
        GROUP BY hour
    ),
    stats AS (
        SELECT AVG(trips)::float   AS mean_trips,
               STDDEV(trips)::float AS std_trips
        FROM hourly
    )
    SELECT h.hour,
           h.trips,
           ROUND(s.mean_trips::numeric, 1)::float AS expected,
           CASE WHEN s.std_trips > 0
                THEN ROUND(((h.trips - s.mean_trips) / s.std_trips)::numeric, 2)::float
                ELSE 0
           END AS zscore
    FROM hourly h, stats s
    ORDER BY h.hour
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Per-hour trip counts with Z-score vs. monthly average — highlights anomalous hours."""
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    filter_sql, filter_params = build_filter_clause(filters)
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, {"data_month": date(year, month, 1), **filter_params})
    return [
        {
            "hour": row.hour,
            "trips": row.trips,
            "expected": row.expected,
            "zscore": row.zscore,
        }
        for row in result.fetchall()
    ]
