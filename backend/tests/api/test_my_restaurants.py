from httpx import AsyncClient

from tests.api.conftest import API, Seeded


async def test_staff_see_their_restaurants(client: AsyncClient, seeded: Seeded, login) -> None:
    waiter = await login(seeded.users["waiter"])
    resp = await client.get(f"{API}/users/me/restaurants", headers=waiter)
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [str(seeded.restaurant.id)]

    # A manager assigned elsewhere sees nothing here.
    outsider = await login(seeded.users["outsider_manager"])
    resp = await client.get(f"{API}/users/me/restaurants", headers=outsider)
    assert resp.json() == []


async def test_admin_sees_all_active_restaurants(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    admin = await login(seeded.users["admin"])
    resp = await client.get(f"{API}/users/me/restaurants", headers=admin)
    assert resp.status_code == 200
    assert any(r["id"] == str(seeded.restaurant.id) for r in resp.json())


async def test_customer_sees_no_restaurants(client: AsyncClient, seeded: Seeded, login) -> None:
    customer = await login(seeded.users["customer"])
    resp = await client.get(f"{API}/users/me/restaurants", headers=customer)
    assert resp.json() == []
