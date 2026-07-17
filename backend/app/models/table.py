import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.models.enums import TableShape, TableStatus


class Table(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tables"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "table_number", name="uq_tables_restaurant_number"),
        Index("ix_tables_restaurant_floor", "restaurant_id", "floor_id"),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    floor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("floors.id", ondelete="CASCADE"), nullable=False
    )
    table_number: Mapped[str] = mapped_column(String(32), nullable=False)

    # Floor-plan geometry — the frontend renders tables from this data, never a static image.
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rotation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    shape: Mapped[TableShape] = mapped_column(
        Enum(
            TableShape,
            name="table_shape",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
        default=TableShape.RECTANGLE,
    )

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    min_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[TableStatus] = mapped_column(
        Enum(
            TableStatus,
            name="table_status",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
        default=TableStatus.AVAILABLE,
        index=True,
    )

    is_indoor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_accessible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="tables")
    floor: Mapped["Floor"] = relationship(back_populates="tables")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="table")
    status_logs: Mapped[list["TableStatusLog"]] = relationship(back_populates="table")

    def __repr__(self) -> str:
        return f"<Table {self.table_number} ({self.status.value})>"
