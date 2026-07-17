import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDPKMixin
from app.models.enums import EmployeeRoleAtRestaurant


class EmployeeRestaurant(UUIDPKMixin, TimestampMixin, Base):
    """Which restaurant(s) a Waiter/Manager account is authorized to act on.

    Kept separate from User.role: User.role says what KIND of actions an
    account can perform in general (Admin is global); this table says WHICH
    restaurant(s) a Waiter/Manager may act on. See docs/architecture.md.
    """

    __tablename__ = "employee_restaurants"
    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id", name="uq_employee_restaurants_user_restaurant"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    role_at_restaurant: Mapped[EmployeeRoleAtRestaurant] = mapped_column(
        Enum(
            EmployeeRoleAtRestaurant,
            name="employee_role_at_restaurant",
            values_callable=lambda e: [x.value for x in e],
            create_type=False,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship(back_populates="employee_restaurants")
    restaurant: Mapped["Restaurant"] = relationship(back_populates="employee_restaurants")

    def __repr__(self) -> str:
        return f"<EmployeeRestaurant user={self.user_id} restaurant={self.restaurant_id}>"
