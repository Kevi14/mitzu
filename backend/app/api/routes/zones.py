from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.core.db import get_db
from app.models.zone import TaxiZone

router = APIRouter(prefix="/api", tags=["zones"])


@router.get("/zones")
async def get_zones(
    _: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TaxiZone).order_by(TaxiZone.location_id))
    zones = result.scalars().all()
    return [
        {"location_id": z.location_id, "borough": z.borough, "zone": z.zone}
        for z in zones
    ]
