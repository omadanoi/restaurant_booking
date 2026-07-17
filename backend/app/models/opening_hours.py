import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin


class OpeningHours(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "opening_hours"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "day_of_week", name="uq_opening_hours_restaurant_day"),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 6=Sunday
    opens_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    closes_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="opening_hours")

    def __repr__(self) -> str:
        return f"<OpeningHours restaurant={self.restaurant_id} day={self.day_of_week}>"
