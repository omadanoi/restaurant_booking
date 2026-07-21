from httpx import AsyncClient

from tests.api.conftest import API, Seeded


async def test_list_elements_public_and_initially_empty(
    client: AsyncClient, seeded: Seeded
) -> None:
    resp = await client.get(f"{API}/restaurants/{seeded.restaurant.id}/elements")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_manager_creates_moves_and_resizes_element(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])

    resp = await client.post(
        f"{API}/restaurants/{rid}/elements",
        json={
            "floor_id": str(seeded.floor.id),
            "element_type": "wall",
            "x": 100,
            "y": 50,
            "width": 200,
            "height": 12,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["element_type"] == "wall"
    element_id = body["id"]

    # Editor drag + resize + rotate = PATCH with new geometry.
    resp = await client.patch(
        f"{API}/restaurants/{rid}/elements/{element_id}",
        json={"x": 300, "y": 150, "width": 260, "height": 14, "rotation": 90},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert (body["x"], body["y"], body["width"], body["rotation"]) == (300, 150, 260, 90)

    # Now visible on the public layout.
    resp = await client.get(f"{API}/restaurants/{rid}/elements")
    assert len(resp.json()) == 1


async def test_labelled_element_roundtrips_caption(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])
    resp = await client.post(
        f"{API}/restaurants/{rid}/elements",
        json={
            "floor_id": str(seeded.floor.id),
            "element_type": "restroom",
            "width": 110,
            "height": 80,
            "label": "Restrooms",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["label"] == "Restrooms"


async def test_waiter_cannot_edit_layout_elements(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["waiter"])
    resp = await client.post(
        f"{API}/restaurants/{rid}/elements",
        json={"floor_id": str(seeded.floor.id), "element_type": "wall"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_manager_deletes_element(client: AsyncClient, seeded: Seeded, login) -> None:
    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])
    resp = await client.post(
        f"{API}/restaurants/{rid}/elements",
        json={"floor_id": str(seeded.floor.id), "element_type": "plant", "width": 40, "height": 40},
        headers=headers,
    )
    element_id = resp.json()["id"]

    resp = await client.delete(f"{API}/restaurants/{rid}/elements/{element_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"{API}/restaurants/{rid}/elements")
    assert resp.json() == []


async def test_create_element_on_foreign_floor_404(
    client: AsyncClient, seeded: Seeded, login
) -> None:
    import uuid

    rid = seeded.restaurant.id
    headers = await login(seeded.users["manager"])
    resp = await client.post(
        f"{API}/restaurants/{rid}/elements",
        json={"floor_id": str(uuid.uuid4()), "element_type": "wall"},
        headers=headers,
    )
    assert resp.status_code == 404
