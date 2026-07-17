import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ReservationSource, ReservationStatus


class ReservationCreate(BaseModel):
    table_id: uuid.UUID
    # AwareDatetime: naive timestamps are ambiguous across restaurant
    # timezones, so the API refuses them outright.
    start_time: AwareDatetime
    end_time: AwareDatetime
    party_size: int = Field(ge=1, le=50)
    special_requests: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def end_after_start(self) -> "ReservationCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ReservationUpdate(BaseModel):
    """Customer-facing modification: time window, party size, requests."""

    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None
    party_size: int | None = Field(default=None, ge=1, le=50)
    special_requests: str | None = Field(default=None, max_length=2000)


class ReservationStatusChange(BaseModel):
    status: ReservationStatus


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_id: uuid.UUID
    table_id: uuid.UUID
    customer_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    party_size: int
    status: ReservationStatus
    source: ReservationSource
    special_requests: str | None
    created_at: datetime


class ReservationListOut(BaseModel):
    items: list[ReservationOut]
    total: int
    limit: int
    offset: int
