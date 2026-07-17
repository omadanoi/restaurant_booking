from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.user import UserListOut, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user


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
