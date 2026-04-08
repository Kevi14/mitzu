from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vendor_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    pickup_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dropoff_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    passenger_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    trip_distance: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    rate_code_id: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    store_and_fwd_flag: Mapped[str | None] = mapped_column(String(1), nullable=True)
    pu_location_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    do_location_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    payment_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fare_amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    extra: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    mta_tax: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    tip_amount: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    tolls_amount: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    improvement_surcharge: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    congestion_surcharge: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    cbd_congestion_fee: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    data_month: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        Index("ix_trips_pickup_datetime", "pickup_datetime"),
        Index("ix_trips_data_month", "data_month"),
        Index("ix_trips_pu_location_id", "pu_location_id"),
        Index("ix_trips_payment_type", "payment_type"),
    )
