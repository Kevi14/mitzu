from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    SELECT z.zone,
           z.borough,
           COUNT(*) AS trips,
           ROUND(AVG(tip_amount / NULLIF(fare_amount, 0)) * 100, 2)::float AS avg_tip_pct,
           ROUND(AVG(tip_amount)::numeric, 2)::float AS avg_tip_usd
    FROM trips t
    JOIN taxi_zones z ON t.pu_location_id = z.location_id
    WHERE t.data_month = :data_month
      AND t.fare_amount > 0
      AND t.payment_type = 1
      {filters}
    GROUP BY z.zone, z.borough
    HAVING COUNT(*) >= 50
    ORDER BY avg_tip_pct DESC
    LIMIT 20
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Top 20 pickup zones by average tip % (credit card trips only)."""
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    filter_sql, filter_params = build_filter_clause(filters, table_alias="t")
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, {"data_month": date(year, month, 1), **filter_params})
    return [
        {
            "zone": row.zone,
            "borough": row.borough,
            "trips": row.trips,
            "avg_tip_pct": row.avg_tip_pct or 0,
            "avg_tip_usd": row.avg_tip_usd or 0,
        }
        for row in result.fetchall()
    ]
