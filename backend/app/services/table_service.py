import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models import Table, TableStatusLog, User
from app.models.enums import TableStatus
from app.repositories.floor import FloorRepository
from app.repositories.table import TableRepository
from app.schemas.table import TableCreate, TableUpdate

logger = get_logger(__name__)


class TableService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tables = TableRepository(db)
        self.floors = FloorRepository(db)

    async def list_for_restaurant(
        self, restaurant_id: uuid.UUID, *, floor_id: uuid.UUID | None = None
    ) -> list[Table]:
        return await self.tables.list_for_restaurant(restaurant_id, floor_id=floor_id)

    async def create(self, restaurant_id: uuid.UUID, data: TableCreate) -> Table:
        floor = await self.floors.get(data.floor_id)
        if floor is None or floor.restaurant_id != restaurant_id:
            raise NotFoundError("Floor not found in this restaurant.")
        try:
            return await self.tables.create({"restaurant_id": restaurant_id, **data.model_dump()})
        except IntegrityError as exc:
            if "uq_tables_restaurant_number" in str(exc.orig):
                raise ConflictError("A table with this number already exists.") from exc
            raise

    async def update(
        self, restaurant_id: uuid.UUID, table_id: uuid.UUID, data: TableUpdate
    ) -> Table:
        table = await self._get(restaurant_id, table_id)
        updates = data.model_dump(exclude_unset=True)
        if "floor_id" in updates:
            floor = await self.floors.get(updates["floor_id"])
            if floor is None or floor.restaurant_id != restaurant_id:
                raise NotFoundError("Floor not found in this restaurant.")
        try:
            return await self.tables.update(table, updates)
        except IntegrityError as exc:
            if "uq_tables_restaurant_number" in str(exc.orig):
                raise ConflictError("A table with this number already exists.") from exc
            raise

    async def deactivate(self, restaurant_id: uuid.UUID, table_id: uuid.UUID) -> Table:
        """Soft delete: keeps reservation history intact."""
        table = await self._get(restaurant_id, table_id)
        return await self.tables.update(table, {"is_active": False})

    async def change_status(
        self,
        staff: User,
        restaurant_id: uuid.UUID,
        table_id: uuid.UUID,
        new_status: TableStatus,
        note: str | None = None,
    ) -> Table:
        """Waiter flow: seat customers, mark cleaning, free the table...
        Every change is logged to table_status_logs with who did it.
        """
        table = await self._get(restaurant_id, table_id)
        old_status = table.status
        table = await self.tables.update(table, {"status": new_status})
        self.db.add(
            TableStatusLog(
                table_id=table.id,
                changed_by=staff.id,
                old_status=old_status,
                new_status=new_status,
                note=note,
            )
        )
        await self.db.flush()
        logger.info(
            "table_status_changed",
            extra={
                "extra_fields": {
                    "table_id": str(table.id),
                    "old": old_status.value,
                    "new": new_status.value,
                    "by": str(staff.id),
                }
            },
        )
        return table

    async def _get(self, restaurant_id: uuid.UUID, table_id: uuid.UUID) -> Table:
        table = await self.tables.get(table_id)
        if table is None or table.restaurant_id != restaurant_id:
            raise NotFoundError("Table not found.")
        return table
