from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    """Average fare breakdown by component — shows what actually drives the bill."""
    query = text("""
        SELECT
            ROUND(AVG(fare_amount)::numeric, 2)::float                          AS base_fare,
            ROUND(AVG(COALESCE(tip_amount, 0))::numeric, 2)::float              AS tip,
            ROUND(AVG(COALESCE(tolls_amount, 0))::numeric, 2)::float            AS tolls,
            ROUND(AVG(COALESCE(extra, 0))::numeric, 2)::float                   AS extras,
            ROUND(AVG(COALESCE(mta_tax, 0))::numeric, 2)::float                 AS mta_tax,
            ROUND(AVG(COALESCE(improvement_surcharge, 0))::numeric, 2)::float   AS surcharge,
            ROUND(AVG(COALESCE(congestion_surcharge, 0))::numeric, 2)::float    AS congestion
        FROM trips
        WHERE data_month = :data_month
          AND fare_amount > 0
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    row = result.fetchone()
    if row is None:
        return []

    return [
        {"component": "Base Fare",   "avg_amount": row.base_fare or 0},
        {"component": "Tip",         "avg_amount": row.tip or 0},
        {"component": "Tolls",       "avg_amount": row.tolls or 0},
        {"component": "Extras",      "avg_amount": row.extras or 0},
        {"component": "MTA Tax",     "avg_amount": row.mta_tax or 0},
        {"component": "Surcharge",   "avg_amount": row.surcharge or 0},
        {"component": "Congestion",  "avg_amount": row.congestion or 0},
    ]
