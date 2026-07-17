import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_restaurant_staff
from app.models import User
from app.schemas.table import TableCreate, TableOut, TableStatusChange, TableUpdate
from app.services.table_service import TableService

router = APIRouter(prefix="/restaurants/{restaurant_id}/tables", tags=["tables"])


def get_table_service(db: AsyncSession = Depends(get_db)) -> TableService:
    return TableService(db)


@router.get("", response_model=list[TableOut])
async def list_tables(
    restaurant_id: uuid.UUID,
    floor_id: uuid.UUID | None = Query(default=None),
    service: TableService = Depends(get_table_service),
) -> list[TableOut]:
    """Public: the data the floor-layout renderer draws from."""
    return await service.list_for_restaurant(restaurant_id, floor_id=floor_id)


@router.post(
    "",
    response_model=TableOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def create_table(
    restaurant_id: uuid.UUID,
    data: TableCreate,
    service: TableService = Depends(get_table_service),
) -> TableOut:
    return await service.create(restaurant_id, data)


@router.patch(
    "/{table_id}",
    response_model=TableOut,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def update_table(
    restaurant_id: uuid.UUID,
    table_id: uuid.UUID,
    data: TableUpdate,
    service: TableService = Depends(get_table_service),
) -> TableOut:
    """Manager: layout edits (drag/rotate/reshape), capacity, availability."""
    return await service.update(restaurant_id, table_id, data)


@router.delete(
    "/{table_id}",
    response_model=TableOut,
    dependencies=[Depends(require_restaurant_staff(manager_only=True))],
)
async def deactivate_table(
    restaurant_id: uuid.UUID,
    table_id: uuid.UUID,
    service: TableService = Depends(get_table_service),
) -> TableOut:
    return await service.deactivate(restaurant_id, table_id)


@router.post("/{table_id}/status", response_model=TableOut)
async def change_table_status(
    restaurant_id: uuid.UUID,
    table_id: uuid.UUID,
    data: TableStatusChange,
    staff: User = Depends(require_restaurant_staff()),
    service: TableService = Depends(get_table_service),
) -> TableOut:
    """Waiter/manager: seat customers, mark cleaning, free the table."""
    return await service.change_status(staff, restaurant_id, table_id, data.status, data.note)
