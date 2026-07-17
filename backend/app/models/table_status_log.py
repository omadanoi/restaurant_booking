import uuid

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.models.enums import TableStatus


class TableStatusLog(UUIDPKMixin, TimestampMixin, Base):
    """History of waiter/manager-driven table status changes.

    Distinct from Reservation status: this tracks the physical table's
    operational state (available/occupied/cleaning/...), which waiters
    update directly regardless of whether a reservation exists.
    """

    __tablename__ = "table_status_logs"
    __table_args__ = (Index("ix_table_status_logs_table_created", "table_id", "created_at"),)

    table_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    old_status: Mapped[TableStatus | None] = mapped_column(
        Enum(
            TableStatus,
            name="table_status",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=True,
    )
    new_status: Mapped[TableStatus] = mapped_column(
        Enum(
            TableStatus,
            name="table_status",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    table: Mapped["Table"] = relationship(back_populates="status_logs")
    reservation: Mapped["Reservation | None"] = relationship(back_populates="status_logs")

    def __repr__(self) -> str:
        return f"<TableStatusLog table={self.table_id} {self.old_status}->{self.new_status}>"
