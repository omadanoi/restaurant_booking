import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin


class Floor(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("restaurant_id", "name", name="uq_floors_restaurant_name"),)

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Canvas dimensions the frontend renders the floor layout against.
    width: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=800.0)
    background_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="floors")
    tables: Mapped[list["Table"]] = relationship(back_populates="floor")

    def __repr__(self) -> str:
        return f"<Floor {self.name} (restaurant={self.restaurant_id})>"
