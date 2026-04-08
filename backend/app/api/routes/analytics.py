from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.core.db import get_db
from app.schemas.analytics import PipelineRequest, PipelineResponse
from app.services.analytics_executor import execute_pipeline

router = APIRouter(prefix="/api", tags=["analytics"])


@router.post("/pipeline/execute", response_model=PipelineResponse)
async def run_pipeline(
    body: PipelineRequest,
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await execute_pipeline(body.nodes, body.edges, db)
