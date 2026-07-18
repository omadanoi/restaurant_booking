"""The double-booking race, tested for real: two independent database
sessions (as two app instances would have) try to book the same table for
overlapping windows simultaneously. Exactly one must win.

This test deliberately does NOT use the savepoint-isolated `db_session`
fixture — real concurrency needs real, separate connections and real
commits, so it seeds its own data and cleans up after itself.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import OverlappingReservationError
from app.core.security import hash_password
from app.models import Floor, Reservation, Restaurant, Table, User
from app.models.enums import TableShape, UserRole
from app.schemas.reservation import ReservationCreate
from app.services.reservation_service import ReservationService
from tests.conftest import TEST_DATABASE_URL


async def test_concurrent_bookings_only_one_wins() -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    marker = uuid.uuid4().hex[:8]
    ids: dict[str, uuid.UUID] = {}

    # -- seed (own committed transaction) ------------------------------------
    async with factory() as db:
        restaurant = Restaurant(
            name=f"RaceTest-{marker}",
            address="1 Race St",
            city="Racetown",
            country="US",
            timezone="UTC",
        )
        db.add(restaurant)
        await db.flush()
        floor = Floor(restaurant_id=restaurant.id, name="Main", level=0)
        db.add(floor)
        await db.flush()
        table = Table(
            restaurant_id=restaurant.id,
            floor_id=floor.id,
            table_number=f"R-{marker}",
            shape=TableShape.RECTANGLE,
            capacity=4,
        )
        customers = [
            User(
                email=f"racer{i}-{marker}@test.com",
                hashed_password=hash_password("irrelevant-pw"),
                full_name=f"Racer {i}",
                role=UserRole.CUSTOMER,
            )
            for i in (1, 2)
        ]
        db.add(table)
        db.add_all(customers)
        await db.flush()
        ids["restaurant"] = restaurant.id
        ids["table"] = table.id
        ids["c1"], ids["c2"] = customers[0].id, customers[1].id
        await db.commit()

    start = (datetime.now(UTC) + timedelta(days=3)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )

    async def attempt(customer_id: uuid.UUID, offset_minutes: int) -> str:
        """One booking attempt in its own session/transaction, like a
        separate request hitting a separate worker.
        """
        async with factory() as db:
            customer = await db.get(User, customer_id)
            assert customer is not None
            service = ReservationService(db)
            data = ReservationCreate(
                table_id=ids["table"],
                start_time=start + timedelta(minutes=offset_minutes),
                end_time=start + timedelta(minutes=offset_minutes + 90),
                party_size=2,
            )
            try:
                await service.create(customer, data)
                await db.commit()
                return "created"
            except OverlappingReservationError:
                await db.rollback()
                return "conflict"

    try:
        # 18:00-19:30 vs 18:30-20:00 — overlapping, fired simultaneously.
        results = await asyncio.gather(attempt(ids["c1"], 0), attempt(ids["c2"], 30))

        assert sorted(results) == ["conflict", "created"], results

        # And the database agrees: exactly one reservation exists.
        async with factory() as db:
            from sqlalchemy import func, select

            count = (
                await db.execute(
                    select(func.count()).select_from(Reservation).where(
                        Reservation.table_id == ids["table"]
                    )
                )
            ).scalar_one()
            assert count == 1
    finally:
        # -- cleanup ---------------------------------------------------------
        async with factory() as db:
            await db.execute(delete(Reservation).where(Reservation.table_id == ids["table"]))
            await db.execute(delete(Table).where(Table.id == ids["table"]))
            await db.execute(delete(Floor).where(Floor.restaurant_id == ids["restaurant"]))
            await db.execute(delete(Restaurant).where(Restaurant.id == ids["restaurant"]))
            await db.execute(delete(User).where(User.id.in_([ids["c1"], ids["c2"]])))
            await db.commit()
        await engine.dispose()


async def test_many_concurrent_bookings_only_one_wins() -> None:
    """Five simultaneous attempts for the exact same slot — one winner."""
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    marker = uuid.uuid4().hex[:8]
    ids: dict[str, uuid.UUID] = {}
    customer_ids: list[uuid.UUID] = []

    async with factory() as db:
        restaurant = Restaurant(
            name=f"RaceTest5-{marker}",
            address="5 Race St",
            city="Racetown",
            country="US",
            timezone="UTC",
        )
        db.add(restaurant)
        await db.flush()
        floor = Floor(restaurant_id=restaurant.id, name="Main", level=0)
        db.add(floor)
        await db.flush()
        table = Table(
            restaurant_id=restaurant.id,
            floor_id=floor.id,
            table_number=f"R5-{marker}",
            shape=TableShape.CIRCLE,
            capacity=4,
        )
        db.add(table)
        for i in range(5):
            u = User(
                email=f"swarm{i}-{marker}@test.com",
                hashed_password=hash_password("irrelevant-pw"),
                full_name=f"Swarm {i}",
                role=UserRole.CUSTOMER,
            )
            db.add(u)
            await db.flush()
            customer_ids.append(u.id)
        await db.flush()
        ids["restaurant"] = restaurant.id
        ids["table"] = table.id
        await db.commit()

    start = (datetime.now(UTC) + timedelta(days=4)).replace(
        hour=19, minute=0, second=0, microsecond=0
    )

    async def attempt(customer_id: uuid.UUID) -> str:
        async with factory() as db:
            customer = await db.get(User, customer_id)
            service = ReservationService(db)
            try:
                await service.create(
                    customer,
                    ReservationCreate(
                        table_id=ids["table"],
                        start_time=start,
                        end_time=start + timedelta(minutes=90),
                        party_size=2,
                    ),
                )
                await db.commit()
                return "created"
            except OverlappingReservationError:
                await db.rollback()
                return "conflict"

    try:
        results = await asyncio.gather(*(attempt(cid) for cid in customer_ids))
        assert results.count("created") == 1, results
        assert results.count("conflict") == 4, results
    finally:
        async with factory() as db:
            await db.execute(delete(Reservation).where(Reservation.table_id == ids["table"]))
            await db.execute(delete(Table).where(Table.id == ids["table"]))
            await db.execute(delete(Floor).where(Floor.restaurant_id == ids["restaurant"]))
            await db.execute(delete(Restaurant).where(Restaurant.id == ids["restaurant"]))
            await db.execute(delete(User).where(User.id.in_(customer_ids)))
            await db.commit()
        await engine.dispose()
