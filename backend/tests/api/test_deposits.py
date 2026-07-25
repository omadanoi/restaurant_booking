"""Booking-deposit lifecycle: manager config, charge at booking, refund on
cancel (both customer and staff paths), forfeit on no-show, decline path.
"""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.api.conftest import API, Seeded

GOOD_CARD = "4242424242424242"
DECLINED_CARD = "4000000000000002"


def _window(days_ahead: int = 7, hour: int = 18) -> tuple[str, str]:
    start = (datetime.now(UTC) + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(hours=1, minutes=30)
    return start.isoformat(), end.isoformat()


async def _enable_deposits(
    client: AsyncClient, headers: dict, restaurant_id, amount: str = "20.00"
):
    return await client.patch(
        f"{API}/restaurants/{restaurant_id}",
        json={"deposit_enabled": True, "deposit_amount": amount, "deposit_currency": "USD"},
        headers=headers,
    )


async def _book(
    client: AsyncClient,
    headers: dict,
    table_id,
    *,
    hour: int = 18,
    card: str | None = GOOD_CARD,
):
    start, end = _window(hour=hour)
    payload: dict = {
        "table_id": str(table_id),
        "start_time": start,
        "end_time": end,
        "party_size": 2,
    }
    if card is not None:
        payload["payment"] = {"card_number": card}
    return await client.post(f"{API}/reservations", json=payload, headers=headers)


async def test_manager_configures_deposits_and_location(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    headers = await login(seeded.users["manager"])
    resp = await client.patch(
        f"{API}/restaurants/{seeded.restaurant.id}",
        json={
            "deposit_enabled": True,
            "deposit_amount": "25.50",
            "deposit_currency": "KGS",
            "latitude": 42.8746,
            "longitude": 74.5698,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deposit_enabled"] is True
    assert body["deposit_amount"] == "25.50"
    assert body["deposit_currency"] == "KGS"
    assert body["latitude"] == 42.8746
    assert body["longitude"] == 74.5698


async def test_non_managers_cannot_configure_deposits(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    for key in ("waiter", "customer"):
        headers = await login(seeded.users[key])
        resp = await _enable_deposits(client, headers, seeded.restaurant.id)
        assert resp.status_code == 403, f"{key}: {resp.text}"


async def test_enabling_deposits_requires_positive_amount(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    headers = await login(seeded.users["manager"])
    resp = await client.patch(
        f"{API}/restaurants/{seeded.restaurant.id}",
        json={"deposit_enabled": True},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_booking_snapshots_deposit_as_paid(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    manager = await login(seeded.users["manager"])
    assert (await _enable_deposits(client, manager, seeded.restaurant.id)).status_code == 200

    customer = await login(seeded.users["customer"])
    resp = await _book(client, customer, seeded.tables["T1"].id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["deposit_status"] == "paid"
    assert body["deposit_amount"] == "20.00"
    assert body["deposit_currency"] == "USD"

    # Later config changes must not touch the snapshot.
    resp = await client.patch(
        f"{API}/restaurants/{seeded.restaurant.id}",
        json={"deposit_amount": "99.00"},
        headers=manager,
    )
    assert resp.status_code == 200
    resp = await client.get(f"{API}/reservations/{body['id']}", headers=customer)
    assert resp.json()["deposit_amount"] == "20.00"


async def test_cancel_refunds_deposit(client: AsyncClient, seeded: Seeded, login) -> None:
    manager = await login(seeded.users["manager"])
    await _enable_deposits(client, manager, seeded.restaurant.id)

    customer = await login(seeded.users["customer"])
    booked = (await _book(client, customer, seeded.tables["T1"].id)).json()

    resp = await client.post(f"{API}/reservations/{booked['id']}/cancel", headers=customer)
    assert resp.status_code == 200, resp.text
    assert resp.json()["deposit_status"] == "refunded"


async def test_staff_cancel_also_refunds(client: AsyncClient, seeded: Seeded, login) -> None:
    manager = await login(seeded.users["manager"])
    await _enable_deposits(client, manager, seeded.restaurant.id)

    customer = await login(seeded.users["customer"])
    booked = (await _book(client, customer, seeded.tables["T1"].id)).json()

    waiter = await login(seeded.users["waiter"])
    resp = await client.post(
        f"{API}/reservations/{booked['id']}/status",
        json={"status": "cancelled"},
        headers=waiter,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["deposit_status"] == "refunded"


async def test_no_show_forfeits_deposit(client: AsyncClient, seeded: Seeded, login) -> None:
    manager = await login(seeded.users["manager"])
    await _enable_deposits(client, manager, seeded.restaurant.id)

    customer = await login(seeded.users["customer"])
    booked = (await _book(client, customer, seeded.tables["T1"].id)).json()
    assert booked["deposit_status"] == "paid"

    waiter = await login(seeded.users["waiter"])
    resp = await client.post(
        f"{API}/reservations/{booked['id']}/status",
        json={"status": "no_show"},
        headers=waiter,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["deposit_status"] == "forfeited"


async def test_declined_card_blocks_booking_but_not_table(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    manager = await login(seeded.users["manager"])
    await _enable_deposits(client, manager, seeded.restaurant.id)

    customer = await login(seeded.users["customer"])
    resp = await _book(client, customer, seeded.tables["T1"].id, card=DECLINED_CARD)
    assert resp.status_code == 402
    assert "declined" in resp.json()["detail"].lower()

    # The failed attempt must not hold the slot.
    resp = await _book(client, customer, seeded.tables["T1"].id, card=GOOD_CARD)
    assert resp.status_code == 201, resp.text
    assert resp.json()["deposit_status"] == "paid"


async def test_no_deposit_when_disabled(client: AsyncClient, seeded: Seeded, login) -> None:
    customer = await login(seeded.users["customer"])
    resp = await _book(client, customer, seeded.tables["T1"].id, card=None)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["deposit_status"] == "none"
    assert body["deposit_amount"] is None
    assert body["deposit_currency"] is None
