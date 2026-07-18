from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import Notification, User
from app.schemas.notification import NotificationListOut, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=NotificationListOut)
async def my_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListOut:
    """The in-app notification feed (all channels are recorded here, so
    this shows the full history regardless of delivery mechanism).
    """
    base = select(Notification).where(Notification.user_id == current_user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    result = await db.execute(
        base.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    )
    return NotificationListOut(
        items=[NotificationOut.model_validate(n) for n in result.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )
