import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.models.enums import DepositStatus, ReservationSource, ReservationStatus


class Reservation(UUIDPKMixin, TimestampMixin, Base):
    """A booking of a single table for a time window.

    Overlap prevention is enforced at the database level by an EXCLUDE
    constraint (see ex_reservations_no_overlap below and ADR 0002) — the
    application-level row-lock + overlap-check added in the service layer
    (Phase 3) is defense-in-depth, not the source of truth.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_reservations_end_after_start"),
        Index("ix_reservations_table_start", "table_id", "start_time"),
        Index("ix_reservations_restaurant_start", "restaurant_id", "start_time"),
        ExcludeConstraint(
            ("table_id", "="),
            (text("tstzrange(start_time, end_time, '[)')"), "&&"),
            where=text("status NOT IN ('cancelled', 'no_show')"),
            using="gist",
            name="ex_reservations_no_overlap",
        ),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            name="reservation_status",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
        default=ReservationStatus.PENDING,
        index=True,
    )
    source: Mapped[ReservationSource] = mapped_column(
        Enum(
            ReservationSource,
            name="reservation_source",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
        default=ReservationSource.ONLINE,
    )
    # Deposit snapshot, frozen at booking time so later config changes never
    # alter what a customer already paid.
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    deposit_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    deposit_status: Mapped[DepositStatus] = mapped_column(
        Enum(
            DepositStatus,
            name="deposit_status",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
        default=DepositStatus.NONE,
    )

    special_requests: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    table: Mapped["Table"] = relationship(back_populates="reservations")
    customer: Mapped["User"] = relationship(back_populates="reservations", foreign_keys=[customer_id])
    status_logs: Mapped[list["TableStatusLog"]] = relationship(back_populates="reservation")
    payments: Mapped[list["Payment"]] = relationship(back_populates="reservation")

    def __repr__(self) -> str:
        return f"<Reservation table={self.table_id} {self.start_time}-{self.end_time}>"
