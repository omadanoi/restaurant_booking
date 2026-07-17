import uuid
from datetime import date, datetime

from sqlalchemy import func, select, text

from app.models import Reservation
from app.models.enums import ReservationStatus
from app.repositories.base import BaseRepository

# Statuses that block a table (mirrors the EXCLUDE constraint's WHERE clause).
ACTIVE_STATUSES = (
    ReservationStatus.PENDING,
    ReservationStatus.CONFIRMED,
    ReservationStatus.SEATED,
    ReservationStatus.COMPLETED,
)


class ReservationRepository(BaseRepository[Reservation]):
    model = Reservation

    async def get_overlapping(
        self,
        table_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        *,
        exclude_reservation_id: uuid.UUID | None = None,
    ) -> list[Reservation]:
        """All active reservations on this table intersecting [start, end).

        Uses the same tstzrange && semantics as the EXCLUDE constraint so
        the pre-check and the constraint can never disagree.
        """
        stmt = (
            select(Reservation)
            .where(
                Reservation.table_id == table_id,
                Reservation.status.in_(ACTIVE_STATUSES),
                text(
                    "tstzrange(start_time, end_time, '[)') && tstzrange(:new_start, :new_end, '[)')"
                ).bindparams(new_start=start_time, new_end=end_time),
            )
        )
        if exclude_reservation_id is not None:
            stmt = stmt.where(Reservation.id != exclude_reservation_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def reserved_table_ids(
        self,
        restaurant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> set[uuid.UUID]:
        """Table ids in this restaurant already booked in [start, end)."""
        result = await self.db.execute(
            select(Reservation.table_id).where(
                Reservation.restaurant_id == restaurant_id,
                Reservation.status.in_(ACTIVE_STATUSES),
                text(
                    "tstzrange(start_time, end_time, '[)') && tstzrange(:new_start, :new_end, '[)')"
                ).bindparams(new_start=start_time, new_end=end_time),
            )
        )
        return set(result.scalars().all())

    async def list_for_customer(
        self, customer_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Reservation], int]:
        base = select(Reservation).where(Reservation.customer_id == customer_id)
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        result = await self.db.execute(
            base.order_by(Reservation.start_time.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total

    async def list_for_restaurant(
        self,
        restaurant_id: uuid.UUID,
        *,
        on_date: date | None = None,
        status: ReservationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Reservation], int]:
        base = select(Reservation).where(Reservation.restaurant_id == restaurant_id)
        if on_date is not None:
            base = base.where(func.date(Reservation.start_time) == on_date)
        if status is not None:
            base = base.where(Reservation.status == status)
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        result = await self.db.execute(
            base.order_by(Reservation.start_time).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total
