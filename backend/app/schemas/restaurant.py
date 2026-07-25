import uuid
from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    address: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="UTC", max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    cuisine_type: str | None = Field(default=None, max_length=120)
    deposit_enabled: bool = False
    deposit_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    deposit_currency: str = Field(default="USD", min_length=3, max_length=3)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def deposit_needs_amount(self) -> "RestaurantCreate":
        if self.deposit_enabled and (self.deposit_amount is None or self.deposit_amount <= 0):
            raise ValueError("deposit_amount must be positive when deposits are enabled")
        return self


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    country: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    cuisine_type: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    # enabled-requires-amount is enforced in RestaurantService.update against
    # the merged state — a PATCH schema can't see fields the client omitted.
    deposit_enabled: bool | None = None
    deposit_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    deposit_currency: str | None = Field(default=None, min_length=3, max_length=3)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    address: str
    city: str
    country: str
    timezone: str
    phone: str | None
    email: str | None
    cuisine_type: str | None
    is_active: bool
    deposit_enabled: bool
    deposit_amount: Decimal | None
    deposit_currency: str
    latitude: float | None
    longitude: float | None


class RestaurantListOut(BaseModel):
    items: list[RestaurantOut]
    total: int
    limit: int
    offset: int


class OpeningHoursItem(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday .. 6=Sunday")
    opens_at: time | None = None
    closes_at: time | None = None
    is_closed: bool = False


class OpeningHoursOut(OpeningHoursItem):
    model_config = ConfigDict(from_attributes=True)


class OpeningHoursSet(BaseModel):
    """Full replacement of a restaurant's weekly schedule."""

    items: list[OpeningHoursItem] = Field(min_length=1, max_length=7)


class HolidayCreate(BaseModel):
    date: date
    is_closed: bool = True
    opens_at: time | None = None
    closes_at: time | None = None
    description: str | None = Field(default=None, max_length=500)


class HolidayOut(HolidayCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
