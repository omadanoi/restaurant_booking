from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_roles
from app.models import EmployeeRestaurant, Restaurant, User
from app.models.enums import UserRole
from app.schemas.restaurant import RestaurantOut
from app.schemas.user import UserListOut, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user


@router.get("/me/restaurants", response_model=list[RestaurantOut])
async def my_restaurants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RestaurantOut]:
    """Restaurants the current user can work in: assigned ones for
    waiters/managers, all active ones for admins, none for customers.
    Drives the staff dashboard's restaurant picker.
    """
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(
            select(Restaurant).where(Restaurant.is_active.is_(True)).order_by(Restaurant.name)
        )
        return list(result.scalars().all())
    result = await db.execute(
        select(Restaurant)
        .join(EmployeeRestaurant, EmployeeRestaurant.restaurant_id == Restaurant.id)
        .where(
            EmployeeRestaurant.user_id == current_user.id,
            EmployeeRestaurant.is_active.is_(True),
            Restaurant.is_active.is_(True),
        )
        .order_by(Restaurant.name)
    )
    return list(result.scalars().all())


@router.get("", response_model=UserListOut)
async def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
    service: UserService = Depends(get_user_service),
) -> UserListOut:
    items, total = await service.list_users(limit=limit, offset=offset)
    return UserListOut(
        items=[UserOut.model_validate(u) for u in items], total=total, limit=limit, offset=offset
    )
