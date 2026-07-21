import uuid

from sqlalchemy import select

from app.models import FloorElement
from app.repositories.base import BaseRepository


class FloorElementRepository(BaseRepository[FloorElement]):
    model = FloorElement

    async def list_for_restaurant(
        self, restaurant_id: uuid.UUID, *, floor_id: uuid.UUID | None = None
    ) -> list[FloorElement]:
        stmt = select(FloorElement).where(FloorElement.restaurant_id == restaurant_id)
        if floor_id is not None:
            stmt = stmt.where(FloorElement.floor_id == floor_id)
        result = await self.db.execute(stmt.order_by(FloorElement.created_at))
        return list(result.scalars().all())
