import uuid

from pydantic import BaseModel, ConfigDict, Field


class FloorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = 0
    width: float = Field(default=1000.0, gt=0)
    height: float = Field(default=800.0, gt=0)
    background_image_url: str | None = Field(default=None, max_length=1000)


class FloorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    level: int | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    background_image_url: str | None = Field(default=None, max_length=1000)


class FloorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_id: uuid.UUID
    name: str
    level: int
    width: float
    height: float
    background_image_url: str | None
