import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.core.db import AsyncSessionLocal, get_db
from app.schemas.ingest import IngestStatusResponse, IngestRequest
from app.services.ingestion import ingest_month

router = APIRouter(prefix="/api", tags=["ingest"])
logger = logging.getLogger(__name__)


async def _run_ingest(year: int, month: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await ingest_month(year, month, db)
    except Exception:
        logger.exception("Background ingest failed for %d-%02d", year, month)


@router.post("/ingest", response_model=IngestStatusResponse)
async def ingest(
    body: IngestRequest,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date
    data_month = date(body.year, body.month, 1)

    result = await db.execute(
        text("SELECT status FROM ingestion_log WHERE data_month = :dm"),
        {"dm": data_month},
    )
    existing = result.fetchone()
    if existing and existing[0] == "success":
        return IngestStatusResponse(status="already_ingested", data_month=str(data_month))

    asyncio.create_task(_run_ingest(body.year, body.month))
    return IngestStatusResponse(status="started", data_month=str(data_month))


@router.get("/ingest/status/{year}/{month}", response_model=IngestStatusResponse)
async def ingest_status(
    year: int,
    month: int,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date
    data_month = date(year, month, 1)

    async with AsyncSessionLocal() as fresh_db:
        # Use READ COMMITTED to see latest committed data
        await fresh_db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        result = await fresh_db.execute(
            text("SELECT status, row_count, error_msg FROM ingestion_log WHERE data_month = :dm"),
            {"dm": data_month},
        )
        row = result.fetchone()
        logger.info("Ingest status for %s: row=%s", data_month, row)

    if not row:
        return IngestStatusResponse(status="not_found", data_month=str(data_month))

    return IngestStatusResponse(
        status=row[0],
        row_count=row[1],
        error_msg=row[2],
        data_month=str(data_month),
    )
