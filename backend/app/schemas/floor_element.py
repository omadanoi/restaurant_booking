import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ElementType


class FloorElementCreate(BaseModel):
    floor_id: uuid.UUID
    element_type: ElementType
    x: float = 0.0
    y: float = 0.0
    width: float = Field(default=100.0, gt=0)
    height: float = Field(default=20.0, gt=0)
    rotation: float = Field(default=0.0, ge=0, lt=360)
    label: str | None = Field(default=None, max_length=120)


class FloorElementUpdate(BaseModel):
    """Partial update — also what the layout editor sends on drag / resize /
    rotate (x/y/width/height/rotation changes).
    """

    floor_id: uuid.UUID | None = None
    element_type: ElementType | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    rotation: float | None = Field(default=None, ge=0, lt=360)
    label: str | None = Field(default=None, max_length=120)


class FloorElementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_id: uuid.UUID
    floor_id: uuid.UUID
    element_type: ElementType
    x: float
    y: float
    width: float
    height: float
    rotation: float
    label: str | None
