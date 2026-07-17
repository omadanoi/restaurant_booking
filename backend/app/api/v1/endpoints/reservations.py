import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_restaurant_staff
from app.models import User
from app.models.enums import ReservationStatus
from app.schemas.reservation import (
    ReservationCreate,
    ReservationListOut,
    ReservationOut,
    ReservationStatusChange,
    ReservationUpdate,
)
from app.schemas.table import TableOut
from app.services.reservation_service import ReservationService

router = APIRouter(tags=["reservations"])


def get_reservation_service(db: AsyncSession = Depends(get_db)) -> ReservationService:
    return ReservationService(db)


# -- availability -------------------------------------------------------------


@router.get("/restaurants/{restaurant_id}/availability", response_model=list[TableOut])
async def find_available_tables(
    restaurant_id: uuid.UUID,
    start_time: AwareDatetime = Query(),
    end_time: AwareDatetime = Query(),
    party_size: int = Query(ge=1, le=50),
    floor_id: uuid.UUID | None = Query(default=None),
    indoor: bool | None = Query(default=None),
    accessible: bool | None = Query(default=None),
    service: ReservationService = Depends(get_reservation_service),
) -> list[TableOut]:
    """Public search: which tables are free for this window and party size."""
    return await service.find_available_tables(
        restaurant_id,
        start_time,
        end_time,
        party_size,
        floor_id=floor_id,
        indoor=indoor,
        accessible=accessible,
    )


# -- customer flows -----------------------------------------------------------


@router.post("/reservations", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    data: ReservationCreate,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationOut:
    return await service.create(current_user, data)


@router.get("/reservations/me", response_model=ReservationListOut)
async def my_reservations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationListOut:
    items, total = await service.reservations.list_for_customer(
        current_user.id, limit=limit, offset=offset
    )
    return ReservationListOut(
        items=[ReservationOut.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/reservations/{reservation_id}", response_model=ReservationOut)
async def get_reservation(
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationOut:
    return await service.get_for_actor(current_user, reservation_id)


@router.patch("/reservations/{reservation_id}", response_model=ReservationOut)
async def modify_reservation(
    reservation_id: uuid.UUID,
    data: ReservationUpdate,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationOut:
    return await service.modify(current_user, reservation_id, data)


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationOut)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationOut:
    return await service.cancel(current_user, reservation_id)


# -- staff flows --------------------------------------------------------------


@router.get(
    "/restaurants/{restaurant_id}/reservations",
    response_model=ReservationListOut,
)
async def restaurant_reservations(
    restaurant_id: uuid.UUID,
    on_date: date | None = Query(default=None, description="Filter to one day (restaurant local)"),
    reservation_status: ReservationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _staff: User = Depends(require_restaurant_staff()),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationListOut:
    """Staff: today's (or any day's) reservation book."""
    items, total = await service.reservations.list_for_restaurant(
        restaurant_id, on_date=on_date, status=reservation_status, limit=limit, offset=offset
    )
    return ReservationListOut(
        items=[ReservationOut.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/reservations/{reservation_id}/status", response_model=ReservationOut)
async def change_reservation_status(
    reservation_id: uuid.UUID,
    data: ReservationStatusChange,
    current_user: User = Depends(get_current_user),
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationOut:
    """Staff lifecycle transitions: confirm, seat, complete, no-show.

    Staff membership of the reservation's restaurant is enforced inside the
    service (the restaurant isn't known until the reservation is loaded).
    """
    reservation = await service.get_for_actor(current_user, reservation_id)
    if reservation.customer_id == current_user.id:
        # Owners use /cancel; status transitions are staff-only.
        from app.core.permissions import check_restaurant_staff

        await check_restaurant_staff(service.db, current_user, reservation.restaurant_id)
    return await service.change_status(current_user, reservation_id, data.status)
