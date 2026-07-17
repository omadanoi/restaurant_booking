from httpx import AsyncClient

from tests.api.conftest import API, Seeded

NEW_RESTAURANT = {
    "name": "New Place",
    "address": "9 New St",
    "city": "Newtown",
    "country": "US",
    "timezone": "Europe/Berlin",
}


async def test_list_restaurants_public(client: AsyncClient, seeded: Seeded) -> None:
    resp = await client.get(f"{API}/restaurants")
    assert resp.status_code == 200
    assert any(r["name"] == seeded.restaurant.name for r in resp.json()["items"])


async def test_create_restaurant_admin_only(client: AsyncClient, seeded: Seeded, login) -> None:
    resp = await client.post(f"{API}/restaurants", json=NEW_RESTAURANT)
    assert resp.status_code == 401  # anonymous

    headers = await login(seeded.users["customer"])
    resp = await client.post(f"{API}/restaurants", json=NEW_RESTAURANT, headers=headers)
    assert resp.status_code == 403  # wrong role

    headers = await login(seeded.users["admin"])
    resp = await client.post(f"{API}/restaurants", json=NEW_RESTAURANT, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["timezone"] == "Europe/Berlin"


async def test_create_restaurant_rejects_bad_timezone(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    headers = await login(seeded.users["admin"])
    resp = await client.post(
        f"{API}/restaurants", json={**NEW_RESTAURANT, "timezone": "Mars/Olympus"}, headers=headers
    )
    assert resp.status_code == 422


async def test_manager_can_update_own_restaurant_only(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])
    resp = await client.patch(
        f"{API}/restaurants/{rid}", json={"description": "Updated"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"

    # A manager not assigned to this restaurant is rejected.
    outsider = await login(seeded.users["outsider_manager"])
    resp = await client.patch(
        f"{API}/restaurants/{rid}", json={"description": "Hacked"}, headers=outsider
    )
    assert resp.status_code == 403


async def test_waiter_cannot_update_restaurant(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["waiter"])
    resp = await client.patch(
        f"{API}/restaurants/{seeded.restaurant.id}", json={"description": "Nope"}, headers=headers
    )
    assert resp.status_code == 403


async def test_admin_can_deactivate_restaurant(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["admin"])
    resp = await client.delete(f"{API}/restaurants/{seeded.restaurant.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Deactivated restaurants disappear from the public list.
    resp = await client.get(f"{API}/restaurants")
    assert all(r["id"] != str(seeded.restaurant.id) for r in resp.json()["items"])


async def test_opening_hours_roundtrip(client: AsyncClient, seeded: Seeded, login) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])
    body = {
        "items": [
            {"day_of_week": 0, "is_closed": True},
            {"day_of_week": 1, "opens_at": "11:00:00", "closes_at": "22:00:00"},
        ]
    }
    resp = await client.put(f"{API}/restaurants/{rid}/opening-hours", json=body, headers=headers)
    assert resp.status_code == 200

    resp = await client.get(f"{API}/restaurants/{rid}/opening-hours")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_opening_hours_validation(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["manager"])
    # closes before opens
    body = {"items": [{"day_of_week": 1, "opens_at": "22:00:00", "closes_at": "11:00:00"}]}
    resp = await client.put(
        f"{API}/restaurants/{seeded.restaurant.id}/opening-hours", json=body, headers=headers
    )
    assert resp.status_code == 422


async def test_holidays_crud(client: AsyncClient, seeded: Seeded, login) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])

    resp = await client.post(
        f"{API}/restaurants/{rid}/holidays",
        json={"date": "2027-12-25", "description": "Christmas"},
        headers=headers,
    )
    assert resp.status_code == 201
    holiday_id = resp.json()["id"]

    # Duplicate date -> conflict.
    resp = await client.post(
        f"{API}/restaurants/{rid}/holidays", json={"date": "2027-12-25"}, headers=headers
    )
    assert resp.status_code == 409

    resp = await client.delete(f"{API}/restaurants/{rid}/holidays/{holiday_id}", headers=headers)
    assert resp.status_code == 204
    resp = await client.get(f"{API}/restaurants/{rid}/holidays")
    assert resp.json() == []
