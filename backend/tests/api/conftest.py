"""Shared fixtures for API tests: seeded users of each role plus a demo
restaurant with floors and tables, all inside the per-test SAVEPOINT.
"""

import uuid
from datetime import time

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import EmployeeRestaurant, Floor, OpeningHours, Restaurant, Table, User
from app.models.enums import EmployeeRoleAtRestaurant, TableShape, UserRole

settings = get_settings()
API = settings.API_V1_STR

PASSWORD = "test-password-123"


class Seeded:
    """Bundle of everything the domain API tests need."""

    def __init__(self) -> None:
        self.restaurant: Restaurant
        self.floor: Floor
        self.tables: dict[str, Table] = {}
        self.users: dict[str, User] = {}


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession) -> Seeded:
    s = Seeded()

    for key, role in {
        "admin": UserRole.ADMIN,
        "manager": UserRole.MANAGER,
        "waiter": UserRole.WAITER,
        "customer": UserRole.CUSTOMER,
        "customer2": UserRole.CUSTOMER,
        "outsider_manager": UserRole.MANAGER,
    }.items():
        user = User(
            email=f"{key}-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password(PASSWORD),
            full_name=f"Test {key}",
            role=role,
        )
        db_session.add(user)
        s.users[key] = user
    await db_session.flush()

    s.restaurant = Restaurant(
        name=f"Testaurant-{uuid.uuid4().hex[:8]}",
        address="1 Test St",
        city="Testville",
        country="US",
        timezone="UTC",
    )
    db_session.add(s.restaurant)
    await db_session.flush()

    db_session.add_all(
        [
            EmployeeRestaurant(
                user_id=s.users["manager"].id,
                restaurant_id=s.restaurant.id,
                role_at_restaurant=EmployeeRoleAtRestaurant.MANAGER,
            ),
            EmployeeRestaurant(
                user_id=s.users["waiter"].id,
                restaurant_id=s.restaurant.id,
                role_at_restaurant=EmployeeRoleAtRestaurant.WAITER,
            ),
        ]
    )

    # Open every day 00:00-23:59 so "future" test times are always valid.
    for day in range(7):
        db_session.add(
            OpeningHours(
                restaurant_id=s.restaurant.id,
                day_of_week=day,
                opens_at=time(0, 0),
                closes_at=time(23, 59),
            )
        )

    s.floor = Floor(restaurant_id=s.restaurant.id, name="Main", level=0)
    db_session.add(s.floor)
    await db_session.flush()

    for number, capacity, indoor, accessible in [
        ("T1", 2, True, False),
        ("T2", 4, True, True),
        ("T3", 8, False, False),
    ]:
        table = Table(
            restaurant_id=s.restaurant.id,
            floor_id=s.floor.id,
            table_number=number,
            shape=TableShape.RECTANGLE,
            capacity=capacity,
            is_indoor=indoor,
            is_accessible=accessible,
        )
        db_session.add(table)
        s.tables[number] = table
    await db_session.flush()

    return s


@pytest_asyncio.fixture
async def login(client: AsyncClient):
    async def _login(user: User) -> dict[str, str]:
        resp = await client.post(
            f"{API}/auth/login", data={"username": user.email, "password": PASSWORD}
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login
