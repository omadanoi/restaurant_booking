import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_restaurant_staff
from app.schemas.floor import FloorCreate, FloorOut, FloorUpdate
from app.services.restaurant_service import RestaurantService

router = APIRouter(prefix="/restaurants/{restaurant_id}/floors", tags=["floors"])


def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


@router.get("", response_model=list[FloorOut])
async def list_floors(
    restaurant_id: uuid.UUID, service: RestaurantService = Depends(get_restaurant_service)
) -> list[FloorOut]:
    return await service.list_floors(restaurant_id)


@router.post(
    "",
    response_model=FloorOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def create_floor(
    restaurant_id: uuid.UUID,
    data: FloorCreate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> FloorOut:
    return await service.create_floor(restaurant_id, data)


@router.patch(
    "/{floor_id}",
    response_model=FloorOut,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def update_floor(
    restaurant_id: uuid.UUID,
    floor_id: uuid.UUID,
    data: FloorUpdate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> FloorOut:
    return await service.update_floor(restaurant_id, floor_id, data)


@router.delete(
    "/{floor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def delete_floor(
    restaurant_id: uuid.UUID,
    floor_id: uuid.UUID,
    service: RestaurantService = Depends(get_restaurant_service),
) -> None:
    await service.delete_floor(restaurant_id, floor_id)
