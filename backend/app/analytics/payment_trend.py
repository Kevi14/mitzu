from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics._filters import build_filter_clause

_SQL = """
    WITH monthly_totals AS (
        SELECT data_month,
               SUM(COUNT(*)) OVER (PARTITION BY data_month) AS total
        FROM trips
        WHERE 1=1
        {filters}
        GROUP BY data_month, payment_type
    ),
    by_type AS (
        SELECT data_month,
               payment_type,
               COUNT(*) AS trips
        FROM trips
        WHERE 1=1
        {filters}
        GROUP BY data_month, payment_type
    )
    SELECT
        b.data_month::text                                        AS data_month,
        ROUND(SUM(b.trips) FILTER (WHERE b.payment_type = 1)
              * 100.0 / NULLIF(MAX(m.total), 0), 1)::float       AS credit_card_pct,
        ROUND(SUM(b.trips) FILTER (WHERE b.payment_type = 2)
              * 100.0 / NULLIF(MAX(m.total), 0), 1)::float       AS cash_pct,
        ROUND(SUM(b.trips) FILTER (WHERE b.payment_type NOT IN (1, 2))
              * 100.0 / NULLIF(MAX(m.total), 0), 1)::float       AS other_pct
    FROM by_type b
    JOIN monthly_totals m ON m.data_month = b.data_month
    GROUP BY b.data_month
    ORDER BY b.data_month
"""


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Credit card vs cash share across all ingested months — ignores month filter."""
    filter_sql, filter_params = build_filter_clause(filters)
    query = text(_SQL.format(filters=filter_sql))
    result = await db.execute(query, filter_params or {})
    return [
        {
            "data_month": row.data_month,
            "credit_card_pct": row.credit_card_pct or 0,
            "cash_pct": row.cash_pct or 0,
            "other_pct": row.other_pct or 0,
        }
        for row in result.fetchall()
    ]
