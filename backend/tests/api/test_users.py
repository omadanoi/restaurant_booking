from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole

settings = get_settings()
API = settings.API_V1_STR


async def _create_user(db: AsyncSession, email: str, role: UserRole) -> tuple[str, str]:
    """Seeds a user directly and returns (email, password)."""
    password = "seeded-password-123"
    db.add(
        User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Seeded User",
            role=role,
        )
    )
    await db.flush()
    return email, password


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/users/me")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


async def test_me_returns_current_user(client: AsyncClient, db_session: AsyncSession) -> None:
    email, password = await _create_user(db_session, "me@example.com", UserRole.CUSTOMER)
    headers = await _login(client, email, password)

    resp = await client.get(f"{API}/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == email


async def test_me_rejects_invalid_token(client: AsyncClient) -> None:
    resp = await client.get(f"{API}/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401


async def test_list_users_forbidden_for_customer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email, password = await _create_user(db_session, "customer@example.com", UserRole.CUSTOMER)
    headers = await _login(client, email, password)

    resp = await client.get(f"{API}/users", headers=headers)
    assert resp.status_code == 403


async def test_list_users_forbidden_for_waiter_and_manager(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    for email, role in [
        ("waiter@example.com", UserRole.WAITER),
        ("manager@example.com", UserRole.MANAGER),
    ]:
        seeded_email, password = await _create_user(db_session, email, role)
        headers = await _login(client, seeded_email, password)
        resp = await client.get(f"{API}/users", headers=headers)
        assert resp.status_code == 403, f"{role} should be forbidden"


async def test_list_users_allowed_for_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    email, password = await _create_user(db_session, "admin@example.com", UserRole.ADMIN)
    headers = await _login(client, email, password)

    resp = await client.get(f"{API}/users", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(u["email"] == email for u in body["items"])


async def test_list_users_pagination_params(client: AsyncClient, db_session: AsyncSession) -> None:
    email, password = await _create_user(db_session, "admin2@example.com", UserRole.ADMIN)
    headers = await _login(client, email, password)

    resp = await client.get(f"{API}/users?limit=1&offset=0", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["limit"] == 1

    resp = await client.get(f"{API}/users?limit=0", headers=headers)
    assert resp.status_code == 422
