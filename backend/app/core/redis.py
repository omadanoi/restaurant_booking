from redis.asyncio import Redis, from_url

from app.core.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    """Process-wide Redis client (connection pooling is internal).

    Kept as a lazy singleton rather than a per-request dependency: the same
    client is shared by request handlers, the WebSocket pub/sub listener,
    and (Phase 5) Celery-adjacent code paths.
    """
    global _client
    if _client is None:
        _client = from_url(get_settings().REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
