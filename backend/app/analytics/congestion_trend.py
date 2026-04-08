from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    SELECT data_month,
           ROUND(AVG(congestion_surcharge)::numeric, 4)::float AS avg_congestion,
           ROUND(SUM(congestion_surcharge)::numeric, 2)::float AS total_congestion,
           COUNT(*) AS trips,
           COUNT(*) FILTER (WHERE congestion_surcharge > 0)::float / COUNT(*) AS pct_charged
    FROM trips
    WHERE 1=1
    {filters}
    GROUP BY data_month
    ORDER BY data_month
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Returns congestion surcharge trend across all ingested months, not just the selected one."""
    filter_sql, filter_params = build_filter_clause(filters)
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, filter_params or {})
    return [
        {
            "data_month": str(row.data_month),
            "avg_congestion": row.avg_congestion or 0,
            "total_congestion": row.total_congestion or 0,
            "trips": row.trips,
            "pct_charged": round((row.pct_charged or 0) * 100, 1),
        }
        for row in result.fetchall()
    ]
