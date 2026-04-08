from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    query = text("""
        SELECT z.zone,
               z.borough,
               COUNT(*) AS trips
        FROM trips t
        JOIN taxi_zones z ON t.pu_location_id = z.location_id
        WHERE t.data_month = :data_month
        GROUP BY z.zone, z.borough
        ORDER BY trips DESC
        LIMIT 20
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    return [{"zone": row.zone, "borough": row.borough, "trips": row.trips} for row in result.fetchall()]
