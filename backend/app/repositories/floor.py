import uuid

from sqlalchemy import select

from app.models import Floor
from app.repositories.base import BaseRepository


class FloorRepository(BaseRepository[Floor]):
    model = Floor

    async def list_for_restaurant(self, restaurant_id: uuid.UUID) -> list[Floor]:
        result = await self.db.execute(
            select(Floor).where(Floor.restaurant_id == restaurant_id).order_by(Floor.level)
        )
        return list(result.scalars().all())
