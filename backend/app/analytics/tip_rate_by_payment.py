from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PAYMENT_LABELS = {1: "Credit Card", 2: "Cash", 3: "No Charge", 4: "Dispute", 5: "Unknown", 6: "Voided"}


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    query = text("""
        SELECT payment_type,
               COUNT(*) AS trips,
               ROUND(AVG(tip_amount / NULLIF(fare_amount, 0)) * 100, 2)::float AS avg_tip_pct,
               ROUND(AVG(tip_amount)::numeric, 2)::float AS avg_tip_usd
        FROM trips
        WHERE data_month = :data_month
          AND fare_amount > 0
        GROUP BY payment_type
        ORDER BY payment_type
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    return [
        {
            "payment_type": row.payment_type,
            "label": PAYMENT_LABELS.get(row.payment_type, "Other"),
            "trips": row.trips,
            "avg_tip_pct": row.avg_tip_pct or 0,
            "avg_tip_usd": row.avg_tip_usd or 0,
        }
        for row in result.fetchall()
    ]
