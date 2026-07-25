from decimal import Decimal

from sqlalchemy import Boolean, Float, Numeric, String
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

    # Booking-deposit policy (deters no-shows and prank bookings). Flat amount
    # per reservation; the reservation snapshots the amount at booking time,
    # so per-guest pricing later is a config-only change.
    deposit_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    deposit_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Map pin, set by the manager (no geocoding service involved).
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    floors: Mapped[list["Floor"]] = relationship(back_populates="restaurant")
    tables: Mapped[list["Table"]] = relationship(back_populates="restaurant")
    opening_hours: Mapped[list["OpeningHours"]] = relationship(back_populates="restaurant")
    holidays: Mapped[list["Holiday"]] = relationship(back_populates="restaurant")
    employee_restaurants: Mapped[list["EmployeeRestaurant"]] = relationship(
        back_populates="restaurant"
    )

    def __repr__(self) -> str:
        return f"<Restaurant {self.name}>"
