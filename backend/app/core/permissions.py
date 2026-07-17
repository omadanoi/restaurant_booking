import uuid
from collections.abc import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import PermissionDeniedError
from app.models import EmployeeRestaurant, User
from app.models.enums import EmployeeRoleAtRestaurant, UserRole


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Dependency factory: the current user must have one of the given roles.

    Usage:
        @router.get("", dependencies=[Depends(require_roles(UserRole.ADMIN))])
    or, when the handler needs the user:
        user: User = Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN))
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise PermissionDeniedError()
        return current_user

    return checker


async def check_restaurant_staff(
    db: AsyncSession,
    user: User,
    restaurant_id: uuid.UUID,
    *,
    manager_only: bool = False,
) -> None:
    """Raises unless `user` may act on this restaurant.

    Admin passes everywhere. Waiters/Managers must have an active
    EmployeeRestaurant row for the restaurant; `manager_only=True`
    additionally requires the manager role there. See docs/architecture.md
    for the role-vs-scope split.
    """
    if user.role == UserRole.ADMIN:
        return
    if user.role not in (UserRole.WAITER, UserRole.MANAGER):
        raise PermissionDeniedError()

    result = await db.execute(
        select(EmployeeRestaurant).where(
            EmployeeRestaurant.user_id == user.id,
            EmployeeRestaurant.restaurant_id == restaurant_id,
            EmployeeRestaurant.is_active.is_(True),
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise PermissionDeniedError("You are not assigned to this restaurant.")
    if manager_only and assignment.role_at_restaurant != EmployeeRoleAtRestaurant.MANAGER:
        raise PermissionDeniedError("Manager role required for this restaurant.")


def require_restaurant_staff(*, manager_only: bool = False) -> Callable[..., User]:
    """Dependency factory for routes with a `restaurant_id` path parameter."""

    async def checker(
        restaurant_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        await check_restaurant_staff(db, current_user, restaurant_id, manager_only=manager_only)
        return current_user

    return checker
