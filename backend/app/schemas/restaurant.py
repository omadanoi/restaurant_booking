import uuid
from datetime import date, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
