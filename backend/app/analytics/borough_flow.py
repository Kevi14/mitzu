from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    SELECT pz.borough AS from_borough,
           dz.borough AS to_borough,
           COUNT(*)   AS trips
    FROM trips t
    JOIN taxi_zones pz ON t.pu_location_id = pz.location_id
    JOIN taxi_zones dz ON t.do_location_id = dz.location_id
    WHERE t.data_month = :data_month
    {filters}
    GROUP BY pz.borough, dz.borough
    ORDER BY pz.borough, dz.borough
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Origin × destination borough trip matrix."""
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    filter_sql, filter_params = build_filter_clause(filters, table_alias="t")
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, {"data_month": date(year, month, 1), **filter_params})
    return [
        {"from_borough": row.from_borough, "to_borough": row.to_borough, "trips": row.trips}
        for row in result.fetchall()
    ]
