from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from tests.api.conftest import API, Seeded


def _window(days_ahead: int = 7, hour: int = 18, duration_hours: float = 1.5) -> tuple[str, str]:
    start = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(hours=duration_hours)
    return start.isoformat(), end.isoformat()


async def _book(
    client: AsyncClient, headers: dict, table_id, *, days_ahead: int = 7, hour: int = 18
):
    start, end = _window(days_ahead, hour)
    return await client.post(
        f"{API}/reservations",
        json={"table_id": str(table_id), "start_time": start, "end_time": end, "party_size": 2},
        headers=headers,
    )


async def test_customer_books_a_table(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["customer"])
    resp = await _book(client, headers, seeded.tables["T1"].id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["table_id"] == str(seeded.tables["T1"].id)


async def test_overlapping_booking_conflict(client: AsyncClient, seeded: Seeded, login) -> None:
    c1 = await login(seeded.users["customer"])
    c2 = await login(seeded.users["customer2"])

    assert (await _book(client, c1, seeded.tables["T1"].id)).status_code == 201

    # Same table, overlapping window (18:00-19:30 vs 19:00-20:30) -> 409.
    start, end = _window(7, 19)
    resp = await client.post(
        f"{API}/reservations",
        json={
            "table_id": str(seeded.tables["T1"].id),
            "start_time": start,
            "end_time": end,
            "party_size": 2,
        },
        headers=c2,
    )
    assert resp.status_code == 409

    # Different table, same window -> fine.
    resp = await _book(client, c2, seeded.tables["T2"].id)
    assert resp.status_code == 201


async def test_booking_validations(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["customer"])
    table_id = str(seeded.tables["T1"].id)  # capacity 2

    # Party too large for the table.
    start, end = _window()
    resp = await client.post(
        f"{API}/reservations",
        json={"table_id": table_id, "start_time": start, "end_time": end, "party_size": 6},
        headers=headers,
    )
    assert resp.status_code == 422

    # In the past.
    past_start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    past_end = (datetime.now(timezone.utc) - timedelta(days=1, hours=-2)).isoformat()
    resp = await client.post(
        f"{API}/reservations",
        json={"table_id": table_id, "start_time": past_start, "end_time": past_end, "party_size": 2},
        headers=headers,
    )
    assert resp.status_code == 422

    # end before start.
    resp = await client.post(
        f"{API}/reservations",
        json={"table_id": table_id, "start_time": end, "end_time": start, "party_size": 2},
        headers=headers,
    )
    assert resp.status_code == 422

    # Naive datetime (no timezone) rejected.
    naive = (datetime.now() + timedelta(days=7)).replace(tzinfo=None).isoformat()
    resp = await client.post(
        f"{API}/reservations",
        json={"table_id": table_id, "start_time": naive, "end_time": end, "party_size": 2},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_cancel_frees_the_slot(client: AsyncClient, seeded: Seeded, login) -> None:
    c1 = await login(seeded.users["customer"])
    c2 = await login(seeded.users["customer2"])
    table_id = seeded.tables["T1"].id

    resp = await _book(client, c1, table_id)
    reservation_id = resp.json()["id"]

    resp = await client.post(f"{API}/reservations/{reservation_id}/cancel", headers=c1)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # The exact same window can now be rebooked by someone else.
    resp = await _book(client, c2, table_id)
    assert resp.status_code == 201


async def test_customer_cannot_touch_others_reservation(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    c1 = await login(seeded.users["customer"])
    c2 = await login(seeded.users["customer2"])

    resp = await _book(client, c1, seeded.tables["T1"].id)
    reservation_id = resp.json()["id"]

    # Other customers can neither see nor cancel it (404, not 403 — no leaking).
    assert (await client.get(f"{API}/reservations/{reservation_id}", headers=c2)).status_code == 404
    assert (
        await client.post(f"{API}/reservations/{reservation_id}/cancel", headers=c2)
    ).status_code == 404


async def test_modify_reservation(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["customer"])
    resp = await _book(client, headers, seeded.tables["T2"].id)
    reservation_id = resp.json()["id"]

    new_start, new_end = _window(8, 19)
    resp = await client.patch(
        f"{API}/reservations/{reservation_id}",
        json={"start_time": new_start, "end_time": new_end, "party_size": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["party_size"] == 3


async def test_my_reservations_history(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["customer"])
    await _book(client, headers, seeded.tables["T1"].id, days_ahead=7)
    await _book(client, headers, seeded.tables["T2"].id, days_ahead=8)

    resp = await client.get(f"{API}/reservations/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_staff_sees_restaurant_reservations(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    customer = await login(seeded.users["customer"])
    resp = await _book(client, customer, seeded.tables["T1"].id)
    assert resp.status_code == 201

    waiter = await login(seeded.users["waiter"])
    resp = await client.get(
        f"{API}/restaurants/{seeded.restaurant.id}/reservations", headers=waiter
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # Customers may not read the restaurant's book.
    resp = await client.get(
        f"{API}/restaurants/{seeded.restaurant.id}/reservations", headers=customer
    )
    assert resp.status_code == 403


async def test_staff_lifecycle_transitions(client: AsyncClient, seeded: Seeded, login) -> None:
    customer = await login(seeded.users["customer"])
    resp = await _book(client, customer, seeded.tables["T1"].id)
    reservation_id = resp.json()["id"]

    waiter = await login(seeded.users["waiter"])
    resp = await client.post(
        f"{API}/reservations/{reservation_id}/status", json={"status": "seated"}, headers=waiter
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "seated"

    # seated -> cancelled is not a legal transition.
    resp = await client.post(
        f"{API}/reservations/{reservation_id}/status", json={"status": "cancelled"}, headers=waiter
    )
    assert resp.status_code == 422

    resp = await client.post(
        f"{API}/reservations/{reservation_id}/status", json={"status": "completed"}, headers=waiter
    )
    assert resp.status_code == 200


async def test_customer_cannot_use_status_endpoint(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    customer = await login(seeded.users["customer"])
    resp = await _book(client, customer, seeded.tables["T1"].id)
    reservation_id = resp.json()["id"]

    resp = await client.post(
        f"{API}/reservations/{reservation_id}/status", json={"status": "seated"}, headers=customer
    )
    assert resp.status_code == 403


async def test_availability_search(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["customer"])
    start, end = _window()

    # All three tables free for party of 2.
    resp = await client.get(
        f"{API}/restaurants/{seeded.restaurant.id}/availability",
        params={"start_time": start, "end_time": end, "party_size": 2},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    # Book T1; it drops out of availability for the overlapping window.
    assert (await _book(client, headers, seeded.tables["T1"].id)).status_code == 201
    resp = await client.get(
        f"{API}/restaurants/{seeded.restaurant.id}/availability",
        params={"start_time": start, "end_time": end, "party_size": 2},
    )
    numbers = [t["table_number"] for t in resp.json()]
    assert "T1" not in numbers and len(numbers) == 2

    # Filters: party of 6 only fits T3 (capacity 8); accessible only T2.
    resp = await client.get(
        f"{API}/restaurants/{seeded.restaurant.id}/availability",
        params={"start_time": start, "end_time": end, "party_size": 6},
    )
    assert [t["table_number"] for t in resp.json()] == ["T3"]

    resp = await client.get(
        f"{API}/restaurants/{seeded.restaurant.id}/availability",
        params={"start_time": start, "end_time": end, "party_size": 2, "accessible": True},
    )
    assert [t["table_number"] for t in resp.json()] == ["T2"]


async def test_opening_hours_enforced(client: AsyncClient, seeded: Seeded, login) -> None:
    manager = await login(seeded.users["manager"])
    # Restrict hours: only 11:00-14:00 on every day.
    body = {
        "items": [
            {"day_of_week": d, "opens_at": "11:00:00", "closes_at": "14:00:00"} for d in range(7)
        ]
    }
    resp = await client.put(
        f"{API}/restaurants/{seeded.restaurant.id}/opening-hours", json=body, headers=manager
    )
    assert resp.status_code == 200

    customer = await login(seeded.users["customer"])
    # 18:00 booking now rejected...
    resp = await _book(client, customer, seeded.tables["T1"].id, hour=18)
    assert resp.status_code == 422
    # ...but a lunch booking passes.
    resp = await _book(client, customer, seeded.tables["T1"].id, hour=12)
    assert resp.status_code == 201, resp.text
