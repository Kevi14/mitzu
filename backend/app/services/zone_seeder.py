import io
import logging

import httpx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ZONE_CSV_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi+_zone_lookup.csv"


async def seed_zones(db: AsyncSession) -> None:
    result = await db.execute(text("SELECT COUNT(*) FROM taxi_zones"))
    count = result.scalar()
    if count and count > 0:
        return

    logger.info("Seeding taxi zones...")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(ZONE_CSV_URL)
            resp.raise_for_status()

        df = pd.read_csv(io.BytesIO(resp.content))
        df.columns = [c.strip().lower() for c in df.columns]
        df = df.rename(columns={
            "locationid": "location_id",
            "service_zone": "service_zone",
        })
        df["borough"] = df["borough"].fillna("Unknown")
        df["zone"] = df["zone"].fillna("Unknown")
        df["service_zone"] = df["service_zone"].fillna("Unknown")

        rows = df[["location_id", "borough", "zone", "service_zone"]].to_dict(orient="records")
        await db.execute(
            text(
                "INSERT INTO taxi_zones (location_id, borough, zone, service_zone) "
                "VALUES (:location_id, :borough, :zone, :service_zone) "
                "ON CONFLICT (location_id) DO NOTHING"
            ),
            rows,
        )
        await db.commit()
        logger.info("Seeded %d taxi zones", len(rows))
    except Exception as exc:
        logger.warning("Zone seeding failed: %s", exc)
