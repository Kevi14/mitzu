from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    SELECT
        COUNT(*) AS total_trips,
        COUNT(*) FILTER (WHERE trip_distance = 0)              AS zero_distance,
        COUNT(*) FILTER (WHERE fare_amount < 0)                AS negative_fare,
        COUNT(*) FILTER (WHERE total_amount < 0)               AS negative_total,
        COUNT(*) FILTER (
            WHERE EXTRACT(epoch FROM (dropoff_datetime - pickup_datetime)) < 60
        )                                                      AS sub_1min_trips,
        COUNT(*) FILTER (WHERE passenger_count = 0)            AS zero_passengers,
        COUNT(*) FILTER (WHERE trip_distance > 100)            AS extreme_distance,
        COUNT(*) FILTER (WHERE fare_amount > 500)              AS extreme_fare
    FROM trips
    WHERE data_month = :data_month
    {filters}
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    filter_sql, filter_params = build_filter_clause(filters)
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, {"data_month": date(year, month, 1), **filter_params})
    row = result.fetchone()
    if row is None:
        return []

    total = row.total_trips or 1  # avoid div/0
    return [
        {"anomaly": k, "count": v, "pct": round(v / total * 100, 2)}
        for k, v in {
            "Zero distance": row.zero_distance,
            "Negative fare": row.negative_fare,
            "Negative total": row.negative_total,
            "Sub-1min trip": row.sub_1min_trips,
            "Zero passengers": row.zero_passengers,
            "Extreme distance (>100mi)": row.extreme_distance,
            "Extreme fare (>$500)": row.extreme_fare,
        }.items()
    ]
