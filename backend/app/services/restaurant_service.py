import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Floor, Holiday, OpeningHours, Restaurant
from app.repositories.floor import FloorRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.floor import FloorCreate, FloorUpdate
from app.schemas.restaurant import (
    HolidayCreate,
    OpeningHoursSet,
    RestaurantCreate,
    RestaurantUpdate,
)


class RestaurantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.restaurants = RestaurantRepository(db)
        self.floors = FloorRepository(db)

    # -- restaurants ----------------------------------------------------------

    async def create(self, data: RestaurantCreate) -> Restaurant:
        self._validate_timezone(data.timezone)
        return await self.restaurants.create(data.model_dump())

    async def get(self, restaurant_id: uuid.UUID) -> Restaurant:
        restaurant = await self.restaurants.get(restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurant not found.")
        return restaurant

    async def search(
        self,
        *,
        city: str | None,
        cuisine_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Restaurant], int]:
        return await self.restaurants.search(
            city=city, cuisine_type=cuisine_type, limit=limit, offset=offset
        )

    async def update(self, restaurant_id: uuid.UUID, data: RestaurantUpdate) -> Restaurant:
        restaurant = await self.get(restaurant_id)
        updates = data.model_dump(exclude_unset=True)
        if "timezone" in updates:
            self._validate_timezone(updates["timezone"])
        return await self.restaurants.update(restaurant, updates)

    async def deactivate(self, restaurant_id: uuid.UUID) -> Restaurant:
        """Soft delete / suspension — reservations and layout survive."""
        restaurant = await self.get(restaurant_id)
        return await self.restaurants.update(restaurant, {"is_active": False})

    # -- opening hours & holidays ---------------------------------------------

    async def get_opening_hours(self, restaurant_id: uuid.UUID) -> list[OpeningHours]:
        await self.get(restaurant_id)
        return await self.restaurants.get_opening_hours(restaurant_id)

    async def set_opening_hours(
        self, restaurant_id: uuid.UUID, data: OpeningHoursSet
    ) -> list[OpeningHours]:
        await self.get(restaurant_id)
        days = [item.day_of_week for item in data.items]
        if len(days) != len(set(days)):
            raise ValidationError("Duplicate day_of_week entries.")
        for item in data.items:
            if not item.is_closed and (item.opens_at is None or item.closes_at is None):
                raise ValidationError(
                    f"Day {item.day_of_week}: opens_at and closes_at are required unless closed."
                )
            if (
                item.opens_at is not None
                and item.closes_at is not None
                and item.closes_at <= item.opens_at
            ):
                raise ValidationError(f"Day {item.day_of_week}: closes_at must be after opens_at.")
        return await self.restaurants.replace_opening_hours(
            restaurant_id, [item.model_dump() for item in data.items]
        )

    async def get_holidays(self, restaurant_id: uuid.UUID) -> list[Holiday]:
        await self.get(restaurant_id)
        return await self.restaurants.get_holidays(restaurant_id)

    async def add_holiday(self, restaurant_id: uuid.UUID, data: HolidayCreate) -> Holiday:
        await self.get(restaurant_id)
        existing = await self.restaurants.get_holiday_for_date(restaurant_id, data.date)
        if existing is not None:
            raise ConflictError("A holiday already exists for this date.")
        holiday = Holiday(restaurant_id=restaurant_id, **data.model_dump())
        self.db.add(holiday)
        await self.db.flush()
        return holiday

    async def remove_holiday(self, restaurant_id: uuid.UUID, holiday_id: uuid.UUID) -> None:
        holidays = await self.get_holidays(restaurant_id)
        holiday = next((h for h in holidays if h.id == holiday_id), None)
        if holiday is None:
            raise NotFoundError("Holiday not found.")
        await self.db.delete(holiday)
        await self.db.flush()

    # -- floors ---------------------------------------------------------------

    async def list_floors(self, restaurant_id: uuid.UUID) -> list[Floor]:
        await self.get(restaurant_id)
        return await self.floors.list_for_restaurant(restaurant_id)

    async def create_floor(self, restaurant_id: uuid.UUID, data: FloorCreate) -> Floor:
        await self.get(restaurant_id)
        existing = await self.floors.list_for_restaurant(restaurant_id)
        if any(f.name == data.name for f in existing):
            raise ConflictError("A floor with this name already exists.")
        return await self.floors.create({"restaurant_id": restaurant_id, **data.model_dump()})

    async def update_floor(
        self, restaurant_id: uuid.UUID, floor_id: uuid.UUID, data: FloorUpdate
    ) -> Floor:
        floor = await self._get_floor(restaurant_id, floor_id)
        return await self.floors.update(floor, data.model_dump(exclude_unset=True))

    async def delete_floor(self, restaurant_id: uuid.UUID, floor_id: uuid.UUID) -> None:
        floor = await self._get_floor(restaurant_id, floor_id)
        await self.floors.delete(floor)

    async def _get_floor(self, restaurant_id: uuid.UUID, floor_id: uuid.UUID) -> Floor:
        floor = await self.floors.get(floor_id)
        if floor is None or floor.restaurant_id != restaurant_id:
            raise NotFoundError("Floor not found.")
        return floor

    @staticmethod
    def _validate_timezone(tz: str) -> None:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError(f"Unknown timezone: {tz}") from None
