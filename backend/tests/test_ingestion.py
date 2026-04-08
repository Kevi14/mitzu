"""
Smoke-test the ingestion pipeline end-to-end without a real DB.

Run inside the container:
  docker exec mitzu-backend-1 .venv/bin/python -m pytest tests/test_ingestion.py -v
"""
import io
import logging
import tempfile
from datetime import date

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _make_parquet_bytes(n_rows: int = 200) -> bytes:
    """Build a minimal in-memory Parquet file that looks like TLC data."""
    data = {
        "VendorID": [1] * n_rows,
        "tpep_pickup_datetime": pd.date_range("2024-01-01", periods=n_rows, freq="10min"),
        "tpep_dropoff_datetime": pd.date_range("2024-01-01 00:15", periods=n_rows, freq="10min"),
        "passenger_count": [2] * n_rows,
        "trip_distance": [1.5] * n_rows,
        "RatecodeID": [1] * n_rows,
        "store_and_fwd_flag": ["N"] * n_rows,
        "PULocationID": [100] * n_rows,
        "DOLocationID": [200] * n_rows,
        "payment_type": [1] * n_rows,
        "fare_amount": [10.0] * n_rows,
        "extra": [0.5] * n_rows,
        "mta_tax": [0.5] * n_rows,
        "tip_amount": [2.0] * n_rows,
        "tolls_amount": [0.0] * n_rows,
        "improvement_surcharge": [0.3] * n_rows,
        "total_amount": [13.3] * n_rows,
        "congestion_surcharge": [2.5] * n_rows,
        "Airport_fee": [0.0] * n_rows,
    }
    df = pd.DataFrame(data)
    table = pa.Table.from_pandas(df)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #

def test_transform_renames_columns():
    from app.services.ingestion import COLUMN_MAP, REQUIRED_COLS

    raw = pd.DataFrame({k: [1] for k in COLUMN_MAP.keys() if k != "cbd_congestion_fee"})
    raw["Airport_fee"] = [0.0]

    from app.services.ingestion import _transform  # type: ignore[attr-defined]

    # _transform is a module-level function — import it directly
    import importlib
    ing = importlib.import_module("app.services.ingestion")
    df = ing._transform(raw.copy(), date(2024, 1, 1))

    assert set(REQUIRED_COLS).issubset(df.columns), f"Missing cols: {set(REQUIRED_COLS) - set(df.columns)}"
    assert "data_month" in df.columns
    assert df["data_month"].iloc[0] == date(2024, 1, 1)


def test_batch_read_parquet():
    """Verify PyArrow can read our fake Parquet in batches."""
    parquet_bytes = _make_parquet_bytes(500)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
        f.write(parquet_bytes)
        tmp_path = f.name

    pf = pq.ParquetFile(tmp_path)
    total = 0
    for batch in pf.iter_batches(batch_size=100):
        df = batch.to_pandas()
        assert len(df) <= 100
        total += len(df)

    assert total == 500, f"Expected 500 rows, got {total}"
    logging.info("Batch read OK: %d rows in %d batches", total, total // 100)


def test_transform_drops_null_required_fields():
    """Rows missing pickup_datetime or location IDs must be dropped."""
    import importlib
    ing = importlib.import_module("app.services.ingestion")

    raw = pd.DataFrame({
        "VendorID": [1, 2],
        "tpep_pickup_datetime": [pd.NaT, pd.Timestamp("2024-01-01")],
        "tpep_dropoff_datetime": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01")],
        "PULocationID": [100, 200],
        "DOLocationID": [200, 300],
    })
    df = ing._transform(raw, date(2024, 1, 1))
    assert len(df) == 1, f"Expected 1 row after null drop, got {len(df)}"


def test_download_url_reachable():
    """
    Live network test — verifies CloudFront returns the Parquet file header.
    Streams only the first 64KB to keep it fast.
    """
    import httpx

    url = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
    with httpx.Client(timeout=30) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            chunk = next(resp.iter_bytes(64 * 1024))

    # Parquet magic bytes: PAR1 at start
    assert chunk[:4] == b"PAR1", f"Expected Parquet magic bytes, got {chunk[:4]!r}"
    logging.info("URL reachable, first chunk: %d bytes, magic: %s", len(chunk), chunk[:4])
