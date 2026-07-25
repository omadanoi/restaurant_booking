import uuid

from sqlalchemy import select

from app.models import Payment
from app.models.enums import PaymentKind, PaymentStatus
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    async def latest_charge(self, reservation_id: uuid.UUID) -> Payment | None:
        """Most recent successful charge — the transaction a refund reverses."""
        stmt = (
            select(Payment)
            .where(
                Payment.reservation_id == reservation_id,
                Payment.kind == PaymentKind.CHARGE,
                Payment.status == PaymentStatus.SUCCEEDED,
            )
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
