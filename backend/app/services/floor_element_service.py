import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import FloorElement
from app.realtime.events import queue_event
from app.repositories.floor import FloorRepository
from app.repositories.floor_element import FloorElementRepository
from app.schemas.floor_element import FloorElementCreate, FloorElementUpdate


class FloorElementService:
    """Manager-editable layout features (walls, doors, windows, restrooms…).

    Non-bookable, so there is no status, no reservations and no soft-delete —
    a removed element is simply gone. Geometry changes broadcast over the same
    realtime channel as table moves so open floor views update in place.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.elements = FloorElementRepository(db)
        self.floors = FloorRepository(db)

    async def list_for_restaurant(
        self, restaurant_id: uuid.UUID, *, floor_id: uuid.UUID | None = None
    ) -> list[FloorElement]:
        return await self.elements.list_for_restaurant(restaurant_id, floor_id=floor_id)

    async def create(
        self, restaurant_id: uuid.UUID, data: FloorElementCreate
    ) -> FloorElement:
        await self._assert_floor(restaurant_id, data.floor_id)
        element = await self.elements.create(
            {"restaurant_id": restaurant_id, **data.model_dump()}
        )
        self._broadcast(element, "element.created")
        return element

    async def update(
        self, restaurant_id: uuid.UUID, element_id: uuid.UUID, data: FloorElementUpdate
    ) -> FloorElement:
        element = await self._get(restaurant_id, element_id)
        updates = data.model_dump(exclude_unset=True)
        if "floor_id" in updates:
            await self._assert_floor(restaurant_id, updates["floor_id"])
        element = await self.elements.update(element, updates)
        self._broadcast(element, "element.updated")
        return element

    async def delete(self, restaurant_id: uuid.UUID, element_id: uuid.UUID) -> None:
        element = await self._get(restaurant_id, element_id)
        floor_id = element.floor_id
        await self.elements.delete(element)
        queue_event(
            self.db,
            restaurant_id,
            "element.deleted",
            {"element_id": str(element_id), "floor_id": str(floor_id)},
        )

    def _broadcast(self, element: FloorElement, event_type: str) -> None:
        queue_event(
            self.db,
            element.restaurant_id,
            event_type,
            {
                "element_id": str(element.id),
                "floor_id": str(element.floor_id),
                "element_type": element.element_type.value,
            },
        )

    async def _assert_floor(self, restaurant_id: uuid.UUID, floor_id: uuid.UUID) -> None:
        floor = await self.floors.get(floor_id)
        if floor is None or floor.restaurant_id != restaurant_id:
            raise NotFoundError("Floor not found in this restaurant.")

    async def _get(
        self, restaurant_id: uuid.UUID, element_id: uuid.UUID
    ) -> FloorElement:
        element = await self.elements.get(element_id)
        if element is None or element.restaurant_id != restaurant_id:
            raise NotFoundError("Floor element not found.")
        return element
