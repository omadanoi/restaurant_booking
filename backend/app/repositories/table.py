import uuid

from sqlalchemy import select

from app.models import Table
from app.repositories.base import BaseRepository


class TableRepository(BaseRepository[Table]):
    model = Table

    async def get_for_update(self, table_id: uuid.UUID) -> Table | None:
        """SELECT ... FOR UPDATE — serializes concurrent bookings of the same
        table. See ADR 0002: this is the fail-fast half of the strategy; the
        EXCLUDE constraint remains the hard guarantee underneath.
        """
        result = await self.db.execute(
            select(Table).where(Table.id == table_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_for_restaurant(
        self,
        restaurant_id: uuid.UUID,
        *,
        floor_id: uuid.UUID | None = None,
        only_active: bool = True,
    ) -> list[Table]:
        stmt = select(Table).where(Table.restaurant_id == restaurant_id)
        if floor_id is not None:
            stmt = stmt.where(Table.floor_id == floor_id)
        if only_active:
            stmt = stmt.where(Table.is_active.is_(True))
        result = await self.db.execute(stmt.order_by(Table.table_number))
        return list(result.scalars().all())
