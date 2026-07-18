import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import Floor, Reservation, Restaurant, Table, User
from app.models.enums import ReservationStatus, TableShape, TableStatus, UserRole


async def test_database_connects(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_btree_gist_extension_installed(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
        )
        assert result.scalar() == 1


async def _seed_table(db_session: AsyncSession) -> Table:
    """Creates the minimal chain of parent rows a Reservation needs, with no
    service-layer code involved — this test proves the DB constraint itself
    works, independent of anything built in Phase 3.
    """
    restaurant = Restaurant(
        name="Test Bistro",
        address="1 Main St",
        city="Testville",
        country="US",
        timezone="UTC",
    )
    db_session.add(restaurant)
    await db_session.flush()

    floor = Floor(restaurant_id=restaurant.id, name="Main Floor")
    db_session.add(floor)
    await db_session.flush()

    table = Table(
        restaurant_id=restaurant.id,
        floor_id=floor.id,
        table_number="T1",
        shape=TableShape.RECTANGLE,
        capacity=4,
        status=TableStatus.AVAILABLE,
    )
    db_session.add(table)
    await db_session.flush()
    return table


async def _make_customer(db_session: AsyncSession) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        hashed_password="not-a-real-hash",
        full_name="Test Customer",
        role=UserRole.CUSTOMER,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_exclude_constraint_rejects_overlapping_reservations(
    db_session: AsyncSession,
) -> None:
    table = await _seed_table(db_session)
    customer = await _make_customer(db_session)

    base = datetime(2026, 8, 1, 18, 0, tzinfo=UTC)

    first = Reservation(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=base,
        end_time=base + timedelta(hours=1, minutes=30),
        party_size=2,
        status=ReservationStatus.CONFIRMED,
    )
    db_session.add(first)
    await db_session.flush()

    # Overlaps [18:00, 19:30) by 30 minutes -> must be rejected by the
    # EXCLUDE constraint (see ADR 0002), not by any application code.
    second = Reservation(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=base + timedelta(hours=1),
        end_time=base + timedelta(hours=2, minutes=30),
        party_size=2,
        status=ReservationStatus.CONFIRMED,
    )
    db_session.add(second)

    with pytest.raises(IntegrityError, match="ex_reservations_no_overlap"):
        await db_session.flush()


async def test_exclude_constraint_allows_back_to_back_reservations(
    db_session: AsyncSession,
) -> None:
    """The range bound is `[)` — half-open — so a reservation ending exactly
    when another begins is NOT an overlap.
    """
    table = await _seed_table(db_session)
    customer = await _make_customer(db_session)

    base = datetime(2026, 8, 1, 18, 0, tzinfo=UTC)

    first = Reservation(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=base,
        end_time=base + timedelta(hours=1, minutes=30),
        party_size=2,
        status=ReservationStatus.CONFIRMED,
    )
    second = Reservation(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=base + timedelta(hours=1, minutes=30),
        end_time=base + timedelta(hours=3),
        party_size=2,
        status=ReservationStatus.CONFIRMED,
    )
    db_session.add_all([first, second])
    await db_session.flush()  # must not raise


async def test_exclude_constraint_ignores_cancelled_reservations(
    db_session: AsyncSession,
) -> None:
    table = await _seed_table(db_session)
    customer = await _make_customer(db_session)

    base = datetime(2026, 8, 1, 18, 0, tzinfo=UTC)

    cancelled = Reservation(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=base,
        end_time=base + timedelta(hours=1, minutes=30),
        party_size=2,
        status=ReservationStatus.CANCELLED,
    )
    db_session.add(cancelled)
    await db_session.flush()

    # Same window, but the prior reservation is cancelled, so this must succeed.
    replacement = Reservation(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=base,
        end_time=base + timedelta(hours=1, minutes=30),
        party_size=2,
        status=ReservationStatus.CONFIRMED,
    )
    db_session.add(replacement)
    await db_session.flush()  # must not raise
