from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()
AUTH = f"{settings.API_V1_STR}/auth"

REGISTER_BODY = {
    "email": "alice@example.com",
    "password": "correct-horse-battery",
    "full_name": "Alice Example",
}


async def _register_and_login(client: AsyncClient) -> dict:
    resp = await client.post(f"{AUTH}/register", json=REGISTER_BODY)
    assert resp.status_code == 201, resp.text
    resp = await client.post(
        f"{AUTH}/login",
        data={"username": REGISTER_BODY["email"], "password": REGISTER_BODY["password"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_register_returns_user_without_password(client: AsyncClient) -> None:
    resp = await client.post(f"{AUTH}/register", json=REGISTER_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == REGISTER_BODY["email"]
    assert body["role"] == "customer"
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflict(client: AsyncClient) -> None:
    assert (await client.post(f"{AUTH}/register", json=REGISTER_BODY)).status_code == 201
    resp = await client.post(f"{AUTH}/register", json=REGISTER_BODY)
    assert resp.status_code == 409


async def test_email_is_case_insensitive(client: AsyncClient) -> None:
    """Browsers auto-capitalize inputs; Alice@… and alice@… are one mailbox."""
    mixed = {**REGISTER_BODY, "email": "Alice@Example.com"}
    resp = await client.post(f"{AUTH}/register", json=mixed)
    assert resp.status_code == 201
    assert resp.json()["email"] == "alice@example.com"  # stored canonically

    # Login works regardless of the casing typed.
    resp = await client.post(
        f"{AUTH}/login",
        data={"username": "ALICE@EXAMPLE.COM", "password": REGISTER_BODY["password"]},
    )
    assert resp.status_code == 200, resp.text

    # And a differently-cased duplicate registration is rejected.
    resp = await client.post(f"{AUTH}/register", json=REGISTER_BODY)
    assert resp.status_code == 409


async def test_register_rejects_invalid_email_and_short_password(client: AsyncClient) -> None:
    bad_email = {**REGISTER_BODY, "email": "not-an-email"}
    assert (await client.post(f"{AUTH}/register", json=bad_email)).status_code == 422

    short_pw = {**REGISTER_BODY, "password": "short"}
    assert (await client.post(f"{AUTH}/register", json=short_pw)).status_code == 422


async def test_login_returns_token_pair(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]


async def test_login_wrong_password_401(client: AsyncClient) -> None:
    await client.post(f"{AUTH}/register", json=REGISTER_BODY)
    resp = await client.post(
        f"{AUTH}/login", data={"username": REGISTER_BODY["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


async def test_login_unknown_email_401(client: AsyncClient) -> None:
    resp = await client.post(
        f"{AUTH}/login", data={"username": "ghost@example.com", "password": "whatever-long"}
    )
    assert resp.status_code == 401


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)

    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # The new refresh token works.
    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert resp.status_code == 200


async def test_refresh_reuse_detection_revokes_family(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)

    # Legitimate rotation.
    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    rotated = resp.json()

    # Replay of the OLD (rotated-out) token — theft signal.
    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401

    # The whole family is dead: even the newest token is now revoked.
    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    tokens = await _register_and_login(client)

    resp = await client.post(f"{AUTH}/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 204

    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


async def test_logout_is_idempotent(client: AsyncClient) -> None:
    resp = await client.post(f"{AUTH}/logout", json={"refresh_token": "unknown-token"})
    assert resp.status_code == 204


async def test_garbage_refresh_token_401(client: AsyncClient) -> None:
    resp = await client.post(f"{AUTH}/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401
