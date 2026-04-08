from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health(_: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db_connected": True}
    except Exception as e:
        return {"status": "error", "db_connected": False, "detail": str(e)}
