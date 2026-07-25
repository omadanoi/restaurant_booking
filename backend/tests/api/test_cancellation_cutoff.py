"""Manager-set cancellation cutoff: customers can't cancel inside the
window; staff always can.
"""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.api.conftest import API, Seeded


def _window(hours_ahead: float) -> tuple[str, str]:
    start = datetime.now(UTC) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=1)
    return start.isoformat(), end.isoformat()


async def _book(client: AsyncClient, headers: dict, table_id, *, hours_ahead: float):
    start, end = _window(hours_ahead)
    resp = await client.post(
        f"{API}/reservations",
        json={"table_id": str(table_id), "start_time": start, "end_time": end, "party_size": 2},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_cutoff(client: AsyncClient, headers: dict, restaurant_id, hours: int):
    resp = await client.patch(
        f"{API}/restaurants/{restaurant_id}",
        json={"cancellation_cutoff_hours": hours},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_customer_blocked_inside_cutoff_staff_not(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    manager = await login(seeded.users["manager"])
    body = await _set_cutoff(client, manager, seeded.restaurant.id, 48)
    assert body["cancellation_cutoff_hours"] == 48

    customer = await login(seeded.users["customer"])
    # 24h ahead — inside the 48h cutoff window.
    booked = await _book(client, customer, seeded.tables["T1"].id, hours_ahead=24)

    resp = await client.post(f"{API}/reservations/{booked['id']}/cancel", headers=customer)
    assert resp.status_code == 422
    assert "48 hours" in resp.json()["detail"]

    # Still confirmed; the waiter can cancel it (phone-call escape hatch).
    waiter = await login(seeded.users["waiter"])
    resp = await client.post(f"{API}/reservations/{booked['id']}/cancel", headers=waiter)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


async def test_customer_can_cancel_outside_cutoff(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    manager = await login(seeded.users["manager"])
    await _set_cutoff(client, manager, seeded.restaurant.id, 48)

    customer = await login(seeded.users["customer"])
    # ~7 days ahead — comfortably outside the window.
    booked = await _book(client, customer, seeded.tables["T1"].id, hours_ahead=24 * 7)

    resp = await client.post(f"{API}/reservations/{booked['id']}/cancel", headers=customer)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


async def test_zero_cutoff_means_cancel_anytime(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    customer = await login(seeded.users["customer"])
    # Default cutoff is 0; booking starts in 2h and cancels fine.
    booked = await _book(client, customer, seeded.tables["T1"].id, hours_ahead=2)
    resp = await client.post(f"{API}/reservations/{booked['id']}/cancel", headers=customer)
    assert resp.status_code == 200, resp.text
