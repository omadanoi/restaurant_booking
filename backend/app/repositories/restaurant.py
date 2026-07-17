import uuid

from sqlalchemy import delete, func, select

from app.models import Holiday, OpeningHours, Restaurant
from app.repositories.base import BaseRepository


class RestaurantRepository(BaseRepository[Restaurant]):
    model = Restaurant

    async def search(
        self,
        *,
        city: str | None = None,
        cuisine_type: str | None = None,
        only_active: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Restaurant], int]:
        stmt = select(Restaurant)
        if only_active:
            stmt = stmt.where(Restaurant.is_active.is_(True))
        if city:
            stmt = stmt.where(Restaurant.city.ilike(city))
        if cuisine_type:
            stmt = stmt.where(Restaurant.cuisine_type.ilike(cuisine_type))

        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        result = await self.db.execute(
            stmt.order_by(Restaurant.name).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_opening_hours(self, restaurant_id: uuid.UUID) -> list[OpeningHours]:
        result = await self.db.execute(
            select(OpeningHours)
            .where(OpeningHours.restaurant_id == restaurant_id)
            .order_by(OpeningHours.day_of_week)
        )
        return list(result.scalars().all())

    async def replace_opening_hours(
        self, restaurant_id: uuid.UUID, items: list[dict]
    ) -> list[OpeningHours]:
        await self.db.execute(
            delete(OpeningHours).where(OpeningHours.restaurant_id == restaurant_id)
        )
        rows = [OpeningHours(restaurant_id=restaurant_id, **item) for item in items]
        self.db.add_all(rows)
        await self.db.flush()
        return rows

    async def get_holidays(self, restaurant_id: uuid.UUID) -> list[Holiday]:
        result = await self.db.execute(
            select(Holiday).where(Holiday.restaurant_id == restaurant_id).order_by(Holiday.date)
        )
        return list(result.scalars().all())

    async def get_holiday_for_date(self, restaurant_id: uuid.UUID, on_date) -> Holiday | None:
        result = await self.db.execute(
            select(Holiday).where(
                Holiday.restaurant_id == restaurant_id, Holiday.date == on_date
            )
        )
        return result.scalar_one_or_none()
