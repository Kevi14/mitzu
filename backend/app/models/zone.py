from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TaxiZone(Base):
    __tablename__ = "taxi_zones"

    location_id: Mapped[int] = mapped_column(primary_key=True)
    borough: Mapped[str] = mapped_column(String(64), nullable=False)
    zone: Mapped[str] = mapped_column(String(128), nullable=False)
    service_zone: Mapped[str] = mapped_column(String(64), nullable=False)
