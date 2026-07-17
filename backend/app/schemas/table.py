import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import TableShape, TableStatus


class TableCreate(BaseModel):
    floor_id: uuid.UUID
    table_number: str = Field(min_length=1, max_length=32)
    x: float = 0.0
    y: float = 0.0
    rotation: float = Field(default=0.0, ge=0, lt=360)
    shape: TableShape = TableShape.RECTANGLE
    capacity: int = Field(ge=1, le=50)
    min_capacity: int | None = Field(default=None, ge=1)
    is_indoor: bool = True
    is_accessible: bool = False

    @model_validator(mode="after")
    def min_capacity_not_above_capacity(self) -> "TableCreate":
        if self.min_capacity is not None and self.min_capacity > self.capacity:
            raise ValueError("min_capacity cannot exceed capacity")
        return self


class TableUpdate(BaseModel):
    """Partial update — also what the drag-and-drop floor editor sends
    (x/y/rotation/shape changes).
    """

    floor_id: uuid.UUID | None = None
    table_number: str | None = Field(default=None, min_length=1, max_length=32)
    x: float | None = None
    y: float | None = None
    rotation: float | None = Field(default=None, ge=0, lt=360)
    shape: TableShape | None = None
    capacity: int | None = Field(default=None, ge=1, le=50)
    min_capacity: int | None = Field(default=None, ge=1)
    is_indoor: bool | None = None
    is_accessible: bool | None = None
    is_active: bool | None = None


class TableStatusChange(BaseModel):
    status: TableStatus
    note: str | None = Field(default=None, max_length=1000)


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_id: uuid.UUID
    floor_id: uuid.UUID
    table_number: str
    x: float
    y: float
    rotation: float
    shape: TableShape
    capacity: int
    min_capacity: int | None
    status: TableStatus
    is_indoor: bool
    is_accessible: bool
    is_active: bool
