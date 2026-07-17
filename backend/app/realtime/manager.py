"""WebSocket connection manager with a Redis pub/sub backbone.

Local WebSocket connections are grouped into per-restaurant rooms. Events
are always published to Redis (channel `restaurant:{id}`) rather than
directly to local sockets, and every app process runs one listener task
that fans incoming messages out to its own room members. This means the
design already works with multiple Uvicorn workers — sockets connected to
worker A still receive events triggered by requests handled by worker B.
"""

import asyncio
import contextlib
import json
import uuid
from typing import Any

from fastapi import WebSocket
from redis.asyncio.client import PubSub

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)

CHANNEL_PATTERN = "restaurant:*"


def channel_for(restaurant_id: uuid.UUID | str) -> str:
    return f"restaurant:{restaurant_id}"


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._listener_task: asyncio.Task | None = None
        self._pubsub: PubSub | None = None

    # -- connection lifecycle -------------------------------------------------

    async def connect(self, restaurant_id: uuid.UUID | str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms.setdefault(channel_for(restaurant_id), set()).add(websocket)

    def disconnect(self, restaurant_id: uuid.UUID | str, websocket: WebSocket) -> None:
        room = self._rooms.get(channel_for(restaurant_id))
        if room is not None:
            room.discard(websocket)
            if not room:
                self._rooms.pop(channel_for(restaurant_id), None)

    # -- publishing -----------------------------------------------------------

    async def publish(
        self, restaurant_id: uuid.UUID | str, event_type: str, data: dict[str, Any]
    ) -> None:
        """Publish through Redis so all workers' rooms receive it."""
        message = json.dumps({"type": event_type, "data": data})
        await get_redis().publish(channel_for(restaurant_id), message)

    # -- redis listener -------------------------------------------------------

    async def start(self) -> None:
        if self._listener_task is not None:
            return
        self._pubsub = get_redis().pubsub()
        await self._pubsub.psubscribe(CHANNEL_PATTERN)
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("realtime_listener_started")

    async def stop(self) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None
        if self._pubsub is not None:
            await self._pubsub.punsubscribe()
            await self._pubsub.aclose()
            self._pubsub = None
        logger.info("realtime_listener_stopped")

    async def _listen(self) -> None:
        assert self._pubsub is not None
        async for message in self._pubsub.listen():
            if message["type"] != "pmessage":
                continue
            channel = message["channel"]
            room = self._rooms.get(channel)
            if not room:
                continue
            dead: list[WebSocket] = []
            for ws in room:
                try:
                    await ws.send_text(message["data"])
                except Exception:
                    dead.append(ws)
            for ws in dead:
                room.discard(ws)


manager = ConnectionManager()
