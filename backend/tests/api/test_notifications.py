from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.api.conftest import API, Seeded


async def _book(client: AsyncClient, headers: dict, table_id) -> dict:
    start = (datetime.now(UTC) + timedelta(days=7)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    resp = await client.post(
        f"{API}/reservations",
        json={
            "table_id": str(table_id),
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=2)).isoformat(),
            "party_size": 2,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_booking_creates_pending_confirmation_notification(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    headers = await login(seeded.users["customer"])
    reservation = await _book(client, headers, seeded.tables["T1"].id)

    resp = await client.get(f"{API}/notifications/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    notification = body["items"][0]
    assert notification["type"] == "reservation_confirmed"
    assert notification["status"] == "pending"
    assert notification["reservation_id"] == reservation["id"]


async def test_cancellation_adds_notification(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["customer"])
    reservation = await _book(client, headers, seeded.tables["T1"].id)

    resp = await client.post(f"{API}/reservations/{reservation['id']}/cancel", headers=headers)
    assert resp.status_code == 200

    resp = await client.get(f"{API}/notifications/me", headers=headers)
    types = [n["type"] for n in resp.json()["items"]]
    assert "reservation_cancelled" in types
    assert "reservation_confirmed" in types


async def test_notifications_are_private(client: AsyncClient, seeded: Seeded, login) -> None:
    c1 = await login(seeded.users["customer"])
    await _book(client, c1, seeded.tables["T1"].id)

    c2 = await login(seeded.users["customer2"])
    resp = await client.get(f"{API}/notifications/me", headers=c2)
    assert resp.json()["total"] == 0

    resp = await client.get(f"{API}/notifications/me")
    assert resp.status_code == 401
