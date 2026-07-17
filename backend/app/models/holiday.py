import uuid
from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin


class Holiday(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("restaurant_id", "date", name="uq_holidays_restaurant_date"),)

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opens_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    closes_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="holidays")

    def __repr__(self) -> str:
        return f"<Holiday restaurant={self.restaurant_id} date={self.date}>"
