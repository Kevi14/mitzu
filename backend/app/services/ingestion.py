import asyncio
import logging
import tempfile
import time
from datetime import date
from pathlib import Path

import httpx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

PARQUET_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year}-{month:02d}.parquet"

COLUMN_MAP = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "RatecodeID": "rate_code_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
    "payment_type": "payment_type",
    "fare_amount": "fare_amount",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge",
    "total_amount": "total_amount",
    "congestion_surcharge": "congestion_surcharge",
    "Airport_fee": "cbd_congestion_fee",
    "cbd_congestion_fee": "cbd_congestion_fee",
}

REQUIRED_COLS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "passenger_count",
    "trip_distance", "rate_code_id", "store_and_fwd_flag", "pu_location_id",
    "do_location_id", "payment_type", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount",
    "congestion_surcharge", "cbd_congestion_fee",
]

BATCH_SIZE = 50_000


def _transform(df: pd.DataFrame, data_month: date) -> pd.DataFrame:
    """Apply all transformations to a DataFrame."""
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    df = df.dropna(subset=["pickup_datetime", "dropoff_datetime", "pu_location_id", "do_location_id"])
    if df.empty:
        return df

    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = None

    df = df[REQUIRED_COLS].copy()

    for col in ["fare_amount", "total_amount", "trip_distance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["data_month"] = data_month
    df["store_and_fwd_flag"] = df["store_and_fwd_flag"].astype(str).str[:1]

    return df


def _insert_batches_sync(parquet_path: str, data_month: date) -> int:
    """Read Parquet in batches and insert via psycopg2. Runs in a thread."""
    import pandas as pd
    from sqlalchemy import create_engine

    engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
    pf = pq.ParquetFile(parquet_path)
    total = 0

    for batch in pf.iter_batches(batch_size=BATCH_SIZE):
        df = batch.to_pandas()

        # Rename columns
        df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

        # Drop rows missing critical fields
        df = df.dropna(subset=["pickup_datetime", "dropoff_datetime", "pu_location_id", "do_location_id"])
        if df.empty:
            continue

        # Fill missing optional columns
        for col in REQUIRED_COLS:
            if col not in df.columns:
                df[col] = None

        df = df[REQUIRED_COLS].copy()

        for col in ["fare_amount", "total_amount", "trip_distance"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["data_month"] = data_month
        df["store_and_fwd_flag"] = df["store_and_fwd_flag"].astype(str).str[:1]

        df.to_sql("trips", con=engine, if_exists="append", index=False, method="multi", chunksize=5000)
        total += len(df)
        logger.info("Inserted batch: %d rows (total so far: %d)", len(df), total)

    engine.dispose()
    return total


async def ingest_month(year: int, month: int, db: AsyncSession) -> dict:
    data_month = date(year, month, 1)
    url = PARQUET_URL.format(year=year, month=month)

    # Idempotency check
    result = await db.execute(
        text("SELECT status FROM ingestion_log WHERE data_month = :dm"),
        {"dm": data_month},
    )
    existing = result.fetchone()
    if existing and existing[0] == "success":
        logger.info("Month %s already ingested, skipping", data_month)
        return {"status": "already_ingested", "row_count": 0, "duration_seconds": 0, "data_month": str(data_month)}

    logger.info("Starting ingestion for %s", data_month)

    await db.execute(
        text(
            "INSERT INTO ingestion_log (data_month, status) VALUES (:dm, 'pending') "
            "ON CONFLICT (data_month) DO UPDATE SET status='pending', error_msg=NULL, updated_at=NOW()"
        ),
        {"dm": data_month},
    )
    await db.commit()

    start = time.time()
    try:
        # Stream download to a temp file — avoids holding the full file in RAM
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name

        logger.info("Starting download: %s", url)
        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                logger.info("Response status: %s, content-type: %s", resp.status_code, resp.headers.get("content-type"))
                with open(tmp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)

        logger.info("Download complete, starting DB insert: %s", tmp_path)

        row_count = await asyncio.get_event_loop().run_in_executor(
            None, _insert_batches_sync, tmp_path, data_month
        )
        duration = round(time.time() - start, 2)

        Path(tmp_path).unlink(missing_ok=True)

        await db.execute(
            text(
                "UPDATE ingestion_log SET status='success', row_count=:rc, updated_at=NOW() "
                "WHERE data_month=:dm"
            ),
            {"rc": row_count, "dm": data_month},
        )
        await db.commit()
        logger.info("Ingested %d rows in %.1fs", row_count, duration)
        return {"status": "success", "row_count": row_count, "duration_seconds": duration, "data_month": str(data_month)}

    except Exception as exc:
        Path(tmp_path).unlink(missing_ok=True)
        await db.execute(
            text(
                "UPDATE ingestion_log SET status='error', error_msg=:msg, updated_at=NOW() "
                "WHERE data_month=:dm"
            ),
            {"msg": str(exc)[:500], "dm": data_month},
        )
        await db.commit()
        logger.error("Ingestion failed for %s: %s", data_month, exc)
        raise
