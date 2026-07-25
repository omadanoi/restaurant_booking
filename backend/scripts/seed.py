"""Seeds the dev database with demo accounts and a demo restaurant.

Idempotent: safe to run repeatedly (skips anything that already exists).

Run from backend/ with the venv active:
    python -m scripts.seed

Demo accounts (password for all: Password123):
    admin@demo.com     - Administrator
    manager@demo.com   - Manager of "Trattoria Demo"
    waiter@demo.com    - Waiter at "Trattoria Demo"
    customer@demo.com  - Customer
"""

import asyncio
from datetime import time
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import (
    EmployeeRestaurant,
    Floor,
    FloorElement,
    OpeningHours,
    Restaurant,
    Table,
    User,
)
from app.models.enums import ElementType, EmployeeRoleAtRestaurant, TableShape, UserRole

PASSWORD = "Password123"

USERS = [
    ("admin@demo.com", "Demo Admin", UserRole.ADMIN),
    ("manager@demo.com", "Demo Manager", UserRole.MANAGER),
    ("waiter@demo.com", "Demo Waiter", UserRole.WAITER),
    ("customer@demo.com", "Demo Customer", UserRole.CUSTOMER),
]

# (number, x, y, rotation, shape, capacity, indoor, accessible)
TABLES = [
    ("T1", 100, 100, 0, TableShape.SQUARE, 2, True, False),
    ("T2", 250, 100, 0, TableShape.SQUARE, 2, True, False),
    ("T3", 400, 100, 0, TableShape.RECTANGLE, 4, True, True),
    ("T4", 600, 100, 90, TableShape.RECTANGLE, 4, True, False),
    ("T5", 100, 300, 0, TableShape.CIRCLE, 6, True, True),
    ("T6", 350, 300, 0, TableShape.CIRCLE, 6, True, False),
    ("T7", 600, 300, 0, TableShape.RECTANGLE, 8, True, False),
    ("P1", 150, 550, 0, TableShape.SQUARE, 2, False, False),
    ("P2", 350, 550, 0, TableShape.SQUARE, 4, False, True),
    ("P3", 550, 550, 0, TableShape.RECTANGLE, 6, False, False),
]

# Non-bookable layout features, so customers can read the room — walls,
# windows, the restrooms, the bar. (indoor?, type, x, y, w, h, rotation, label)
# Main Dining is 800x450; Patio is 800x250.
ELEMENTS = [
    # Main Dining — perimeter walls
    (True, ElementType.WALL, 400, 6, 800, 12, 0, None),
    (True, ElementType.WALL, 400, 444, 800, 12, 0, None),
    (True, ElementType.WALL, 6, 225, 450, 12, 90, None),
    (True, ElementType.WALL, 794, 225, 450, 12, 90, None),
    # Windows along the top wall — these make T1–T4 "window tables"
    (True, ElementType.WINDOW, 200, 6, 130, 10, 0, None),
    (True, ElementType.WINDOW, 500, 6, 130, 10, 0, None),
    # Bar, restrooms, entrance
    (True, ElementType.BAR, 150, 400, 220, 55, 0, "Bar"),
    (True, ElementType.RESTROOM, 710, 390, 130, 90, 0, "Restrooms"),
    (True, ElementType.ENTRANCE, 400, 444, 90, 16, 0, "Entrance"),
    # Patio — a boundary wall and a few plants
    (False, ElementType.WALL, 400, 6, 800, 12, 0, None),
    (False, ElementType.PLANT, 60, 70, 44, 44, 0, None),
    (False, ElementType.PLANT, 740, 70, 44, 44, 0, None),
    (False, ElementType.PLANT, 400, 210, 44, 44, 0, None),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        users: dict[str, User] = {}
        for email, name, role in USERS:
            existing = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing:
                users[email] = existing
                continue
            user = User(
                email=email,
                hashed_password=hash_password(PASSWORD),
                full_name=name,
                role=role,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
            users[email] = user
            print(f"created user {email} ({role.value})")

        restaurant = (
            await db.execute(select(Restaurant).where(Restaurant.name == "Trattoria Demo"))
        ).scalar_one_or_none()
        if restaurant is None:
            restaurant = Restaurant(
                name="Trattoria Demo",
                description="Cozy demo trattoria with indoor dining and a patio.",
                address="42 Demo Street",
                city="Springfield",
                country="US",
                timezone="America/New_York",
                cuisine_type="Italian",
                phone="+1-555-0100",
                email="hello@trattoria-demo.test",
                deposit_enabled=True,
                deposit_amount=Decimal("15.00"),
                deposit_currency="USD",
                latitude=39.7817,
                longitude=-89.6501,
            )
            db.add(restaurant)
            await db.flush()
            print("created restaurant Trattoria Demo")

            db.add_all(
                [
                    EmployeeRestaurant(
                        user_id=users["manager@demo.com"].id,
                        restaurant_id=restaurant.id,
                        role_at_restaurant=EmployeeRoleAtRestaurant.MANAGER,
                    ),
                    EmployeeRestaurant(
                        user_id=users["waiter@demo.com"].id,
                        restaurant_id=restaurant.id,
                        role_at_restaurant=EmployeeRoleAtRestaurant.WAITER,
                    ),
                ]
            )

            # Open 11:00-22:00 every day except Monday (closed).
            for day in range(7):
                db.add(
                    OpeningHours(
                        restaurant_id=restaurant.id,
                        day_of_week=day,
                        opens_at=None if day == 0 else time(11, 0),
                        closes_at=None if day == 0 else time(22, 0),
                        is_closed=(day == 0),
                    )
                )

            main_floor = Floor(
                restaurant_id=restaurant.id, name="Main Dining", level=0, width=800, height=450
            )
            patio = Floor(
                restaurant_id=restaurant.id, name="Patio", level=0, width=800, height=250
            )
            db.add_all([main_floor, patio])
            await db.flush()

            for number, x, y, rotation, shape, capacity, indoor, accessible in TABLES:
                db.add(
                    Table(
                        restaurant_id=restaurant.id,
                        floor_id=main_floor.id if indoor else patio.id,
                        table_number=number,
                        x=x,
                        y=y,
                        rotation=rotation,
                        shape=shape,
                        capacity=capacity,
                        is_indoor=indoor,
                        is_accessible=accessible,
                    )
                )
            print(f"created 2 floors and {len(TABLES)} tables")

        # Deposit config + map pin — backfilled idempotently so an already-seeded
        # database (created before this feature) gets them on a re-run.
        if restaurant.latitude is None:
            restaurant.deposit_enabled = True
            restaurant.deposit_amount = Decimal("15.00")
            restaurant.deposit_currency = "USD"
            restaurant.latitude = 39.7817
            restaurant.longitude = -89.6501
            print("backfilled deposit config and map coordinates")

        # Layout elements — seeded idempotently on their own so an already-seeded
        # demo database (created before this feature) gets them on a re-run.
        has_elements = (
            await db.execute(
                select(FloorElement).where(FloorElement.restaurant_id == restaurant.id).limit(1)
            )
        ).scalar_one_or_none()
        if has_elements is None:
            floors_by_name = {
                f.name: f
                for f in (
                    await db.execute(select(Floor).where(Floor.restaurant_id == restaurant.id))
                ).scalars()
            }
            main_floor = floors_by_name.get("Main Dining")
            patio = floors_by_name.get("Patio")
            if main_floor and patio:
                for indoor, element_type, x, y, w, h, rotation, label in ELEMENTS:
                    db.add(
                        FloorElement(
                            restaurant_id=restaurant.id,
                            floor_id=main_floor.id if indoor else patio.id,
                            element_type=element_type,
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            rotation=rotation,
                            label=label,
                        )
                    )
                print(f"created {len(ELEMENTS)} layout elements")

        await db.commit()
        print("seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
