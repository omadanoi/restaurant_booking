import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt operates on at most 72 bytes; cap well below that.
    password: str = Field(min_length=8, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("email", mode="after")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        # Stored canonically in lowercase; lookups are case-insensitive too
        # (see UserRepository.get_by_email) for rows that predate this.
        return v.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int
