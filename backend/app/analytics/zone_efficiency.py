from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Top 20 pickup zones by revenue per minute (driver efficiency proxy)."""
    query = text("""
        SELECT z.zone,
               z.borough,
               COUNT(*) AS trips,
               ROUND(
                   AVG(
                       total_amount / NULLIF(
                           EXTRACT(epoch FROM (dropoff_datetime - pickup_datetime)) / 60.0,
                           0
                       )
                   )::numeric, 2
               )::float AS revenue_per_min
        FROM trips t
        JOIN taxi_zones z ON t.pu_location_id = z.location_id
        WHERE t.data_month = :data_month
          AND t.total_amount > 0
          AND EXTRACT(epoch FROM (dropoff_datetime - pickup_datetime)) > 60
        GROUP BY z.zone, z.borough
        HAVING COUNT(*) >= 50
        ORDER BY revenue_per_min DESC
        LIMIT 20
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    return [
        {
            "zone": row.zone,
            "borough": row.borough,
            "trips": row.trips,
            "revenue_per_min": row.revenue_per_min or 0,
        }
        for row in result.fetchall()
    ]
