from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def run(params: dict, filters: dict, db: AsyncSession) -> list[dict]:
    query = text("""
        SELECT trip_distance::float AS trip_distance,
               fare_amount::float   AS fare_amount
        FROM trips
        WHERE data_month = :data_month
          AND trip_distance > 0
          AND fare_amount > 0
        ORDER BY RANDOM()
        LIMIT 5000
    """)
    year, month = params.get("year"), params.get("month")
    if year is None or month is None:
        return []
    result = await db.execute(query, {"data_month": date(year, month, 1)})
    rows = result.fetchall()

    df = pd.DataFrame(rows, columns=["trip_distance", "fare_amount"])
    q1 = df["fare_amount"].quantile(0.25)
    q3 = df["fare_amount"].quantile(0.75)
    iqr = q3 - q1
    df["is_outlier"] = (df["fare_amount"] < q1 - 1.5 * iqr) | (df["fare_amount"] > q3 + 1.5 * iqr)

    return df.to_dict(orient="records")  # type: ignore[return-value]
