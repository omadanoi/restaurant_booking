import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: NotificationType
    channel: NotificationChannel
    status: NotificationStatus
    payload: dict[str, Any]
    reservation_id: uuid.UUID | None
    restaurant_id: uuid.UUID | None
    sent_at: datetime | None
    created_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    total: int
    limit: int
    offset: int
