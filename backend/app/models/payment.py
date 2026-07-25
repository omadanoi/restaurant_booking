import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.models.enums import PaymentKind, PaymentStatus


class Payment(UUIDPKMixin, TimestampMixin, Base):
    """Audit trail of deposit money movements (charges and refunds).

    One row per provider transaction. Kept separate from the reservation's
    deposit snapshot because a real payment provider will need the provider
    transaction ids for reconciliation and dispute handling.
    """

    __tablename__ = "payments"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[PaymentKind] = mapped_column(
        Enum(
            PaymentKind,
            name="payment_kind",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_txn_id: Mapped[str] = mapped_column(String(128), nullable=False)

    reservation: Mapped["Reservation"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.kind} {self.amount} {self.currency} ({self.status})>"
