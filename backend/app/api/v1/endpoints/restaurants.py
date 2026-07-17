import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_restaurant_staff, require_roles
from app.models.enums import UserRole
from app.schemas.restaurant import (
    HolidayCreate,
    HolidayOut,
    OpeningHoursOut,
    OpeningHoursSet,
    RestaurantCreate,
    RestaurantListOut,
    RestaurantOut,
    RestaurantUpdate,
)
from app.services.restaurant_service import RestaurantService

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


@router.post(
    "",
    response_model=RestaurantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def create_restaurant(
    data: RestaurantCreate, service: RestaurantService = Depends(get_restaurant_service)
) -> RestaurantOut:
    return await service.create(data)


@router.get("", response_model=RestaurantListOut)
async def list_restaurants(
    city: str | None = Query(default=None),
    cuisine_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantListOut:
    items, total = await service.search(
        city=city, cuisine_type=cuisine_type, limit=limit, offset=offset
    )
    return RestaurantListOut(
        items=[RestaurantOut.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{restaurant_id}", response_model=RestaurantOut)
async def get_restaurant(
    restaurant_id: uuid.UUID, service: RestaurantService = Depends(get_restaurant_service)
) -> RestaurantOut:
    return await service.get(restaurant_id)


@router.patch(
    "/{restaurant_id}",
    response_model=RestaurantOut,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def update_restaurant(
    restaurant_id: uuid.UUID,
    data: RestaurantUpdate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantOut:
    return await service.update(restaurant_id, data)


@router.delete(
    "/{restaurant_id}",
    response_model=RestaurantOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def deactivate_restaurant(
    restaurant_id: uuid.UUID, service: RestaurantService = Depends(get_restaurant_service)
) -> RestaurantOut:
    return await service.deactivate(restaurant_id)


# -- opening hours & holidays -------------------------------------------------


@router.get("/{restaurant_id}/opening-hours", response_model=list[OpeningHoursOut])
async def get_opening_hours(
    restaurant_id: uuid.UUID, service: RestaurantService = Depends(get_restaurant_service)
) -> list[OpeningHoursOut]:
    return await service.get_opening_hours(restaurant_id)


@router.put(
    "/{restaurant_id}/opening-hours",
    response_model=list[OpeningHoursOut],
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def set_opening_hours(
    restaurant_id: uuid.UUID,
    data: OpeningHoursSet,
    service: RestaurantService = Depends(get_restaurant_service),
) -> list[OpeningHoursOut]:
    return await service.set_opening_hours(restaurant_id, data)


@router.get("/{restaurant_id}/holidays", response_model=list[HolidayOut])
async def get_holidays(
    restaurant_id: uuid.UUID, service: RestaurantService = Depends(get_restaurant_service)
) -> list[HolidayOut]:
    return await service.get_holidays(restaurant_id)


@router.post(
    "/{restaurant_id}/holidays",
    response_model=HolidayOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def add_holiday(
    restaurant_id: uuid.UUID,
    data: HolidayCreate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> HolidayOut:
    return await service.add_holiday(restaurant_id, data)


@router.delete(
    "/{restaurant_id}/holidays/{holiday_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def remove_holiday(
    restaurant_id: uuid.UUID,
    holiday_id: uuid.UUID,
    service: RestaurantService = Depends(get_restaurant_service),
) -> None:
    await service.remove_holiday(restaurant_id, holiday_id)
