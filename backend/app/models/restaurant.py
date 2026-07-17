from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin


class Restaurant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cuisine_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    floors: Mapped[list["Floor"]] = relationship(back_populates="restaurant")
    tables: Mapped[list["Table"]] = relationship(back_populates="restaurant")
    opening_hours: Mapped[list["OpeningHours"]] = relationship(back_populates="restaurant")
    holidays: Mapped[list["Holiday"]] = relationship(back_populates="restaurant")
    employee_restaurants: Mapped[list["EmployeeRestaurant"]] = relationship(
        back_populates="restaurant"
    )

    def __repr__(self) -> str:
        return f"<Restaurant {self.name}>"
