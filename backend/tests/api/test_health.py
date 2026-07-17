from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_db_health(client: AsyncClient) -> None:
    response = await client.get(f"{settings.API_V1_STR}/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
