from collections.abc import Callable

from fastapi import Depends

from app.api.deps import get_current_user
from app.core.exceptions import PermissionDeniedError
from app.models import User
from app.models.enums import UserRole


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
