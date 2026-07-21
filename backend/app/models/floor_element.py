import uuid

from sqlalchemy import Enum, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.models.enums import ElementType


class FloorElement(UUIDPKMixin, TimestampMixin, Base):
    """A non-bookable feature on the floor plan — a wall, door, window,
    restroom, bar, etc. Pure geometry the frontend renders behind the tables,
    exactly like a Table but never selectable or reservable.

    Every element is modelled as a (possibly rotated) rectangle so the whole
    floor — tables and features alike — shares one x/y/width/height/rotation
    geometry model. A wall is just a long, thin rectangle.
    """

    __tablename__ = "floor_elements"
    __table_args__ = (
        Index("ix_floor_elements_restaurant_floor", "restaurant_id", "floor_id"),
    )

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    floor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("floors.id", ondelete="CASCADE"), nullable=False
    )

    element_type: Mapped[ElementType] = mapped_column(
        Enum(
            ElementType,
            name="element_type",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
    )

    # Floor-plan geometry — center point, size, rotation (degrees).
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    rotation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Optional caption drawn on the element (e.g. "Restrooms", "Bar").
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    restaurant: Mapped["Restaurant"] = relationship()
    floor: Mapped["Floor"] = relationship(back_populates="elements")

    def __repr__(self) -> str:
        return f"<FloorElement {self.element_type.value} (floor={self.floor_id})>"
