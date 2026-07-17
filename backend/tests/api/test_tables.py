from httpx import AsyncClient

from tests.api.conftest import API, Seeded


async def test_list_tables_public_renders_layout_data(
    client: AsyncClient, seeded: Seeded
) -> None:
    resp = await client.get(f"{API}/restaurants/{seeded.restaurant.id}/tables")
    assert resp.status_code == 200
    tables = resp.json()
    assert len(tables) == 3
    # The layout fields the frontend renders from are all present.
    for field in ("x", "y", "rotation", "shape", "capacity", "status"):
        assert field in tables[0]


async def test_manager_creates_and_moves_table(client: AsyncClient, seeded: Seeded, login) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])

    resp = await client.post(
        f"{API}/restaurants/{rid}/tables",
        json={
            "floor_id": str(seeded.floor.id),
            "table_number": "T9",
            "x": 10,
            "y": 20,
            "capacity": 4,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    table_id = resp.json()["id"]

    # Drag-and-drop = PATCH with new coordinates/rotation.
    resp = await client.patch(
        f"{API}/restaurants/{rid}/tables/{table_id}",
        json={"x": 300, "y": 150, "rotation": 45},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert (body["x"], body["y"], body["rotation"]) == (300, 150, 45)


async def test_duplicate_table_number_conflict(client: AsyncClient, seeded: Seeded, login) -> None:
    headers = await login(seeded.users["manager"])
    resp = await client.post(
        f"{API}/restaurants/{seeded.restaurant.id}/tables",
        json={"floor_id": str(seeded.floor.id), "table_number": "T1", "capacity": 2},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_waiter_cannot_edit_layout_but_can_change_status(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    rid = seeded.restaurant.id
    table_id = seeded.tables["T1"].id
    headers = await login(seeded.users["waiter"])

    resp = await client.patch(
        f"{API}/restaurants/{rid}/tables/{table_id}", json={"x": 999}, headers=headers
    )
    assert resp.status_code == 403  # layout edits are manager-only

    resp = await client.post(
        f"{API}/restaurants/{rid}/tables/{table_id}/status",
        json={"status": "occupied", "note": "Walk-in party of 2"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "occupied"

    resp = await client.post(
        f"{API}/restaurants/{rid}/tables/{table_id}/status",
        json={"status": "cleaning"},
        headers=headers,
    )
    assert resp.status_code == 200
    resp = await client.post(
        f"{API}/restaurants/{rid}/tables/{table_id}/status",
        json={"status": "available"},
        headers=headers,
    )
    assert resp.status_code == 200


async def test_customer_cannot_change_table_status(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    headers = await login(seeded.users["customer"])
    resp = await client.post(
        f"{API}/restaurants/{seeded.restaurant.id}/tables/{seeded.tables['T1'].id}/status",
        json={"status": "occupied"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_soft_delete_table(client: AsyncClient, seeded: Seeded, login) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])
    resp = await client.delete(
        f"{API}/restaurants/{rid}/tables/{seeded.tables['T3'].id}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = await client.get(f"{API}/restaurants/{rid}/tables")
    assert len(resp.json()) == 2  # inactive tables hidden from layout
