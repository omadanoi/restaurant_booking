import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_restaurant_staff
from app.schemas.floor_element import (
    FloorElementCreate,
    FloorElementOut,
    FloorElementUpdate,
)
from app.services.floor_element_service import FloorElementService

router = APIRouter(prefix="/restaurants/{restaurant_id}/elements", tags=["floor-elements"])


def get_element_service(db: AsyncSession = Depends(get_db)) -> FloorElementService:
    return FloorElementService(db)


@router.get("", response_model=list[FloorElementOut])
async def list_elements(
    restaurant_id: uuid.UUID,
    floor_id: uuid.UUID | None = Query(default=None),
    service: FloorElementService = Depends(get_element_service),
) -> list[FloorElementOut]:
    """Public: the non-bookable layout features the floor renderer draws."""
    return await service.list_for_restaurant(restaurant_id, floor_id=floor_id)


@router.post(
    "",
    response_model=FloorElementOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def create_element(
    restaurant_id: uuid.UUID,
    data: FloorElementCreate,
    service: FloorElementService = Depends(get_element_service),
) -> FloorElementOut:
    return await service.create(restaurant_id, data)


@router.patch(
    "/{element_id}",
    response_model=FloorElementOut,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def update_element(
    restaurant_id: uuid.UUID,
    element_id: uuid.UUID,
    data: FloorElementUpdate,
    service: FloorElementService = Depends(get_element_service),
) -> FloorElementOut:
    """Manager: layout edits — drag (x/y), resize (width/height), rotate."""
    return await service.update(restaurant_id, element_id, data)


@router.delete(
    "/{element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def delete_element(
    restaurant_id: uuid.UUID,
    element_id: uuid.UUID,
    service: FloorElementService = Depends(get_element_service),
) -> None:
    await service.delete(restaurant_id, element_id)
