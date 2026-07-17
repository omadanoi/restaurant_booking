"""Realtime layer tests against a real Redis (Memurai locally, service
container in CI). The WebSocket endpoint itself is exercised in
tests/api/test_ws.py; here we test the pub/sub fan-out machinery and the
post-commit event queue.
"""

import asyncio
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.realtime.events import discard_queued, publish_queued, queue_event
from app.realtime.manager import ConnectionManager, channel_for


class StubWebSocket:
    """Just enough of the WebSocket interface for ConnectionManager."""

    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


async def _wait_for(condition, timeout: float = 3.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.05)


async def test_pubsub_fanout_to_room_members() -> None:
    manager = ConnectionManager()
    await manager.start()
    restaurant_id = uuid.uuid4()
    other_restaurant_id = uuid.uuid4()

    ws1, ws2, ws_other = StubWebSocket(), StubWebSocket(), StubWebSocket()
    try:
        await manager.connect(restaurant_id, ws1)
        await manager.connect(restaurant_id, ws2)
        await manager.connect(other_restaurant_id, ws_other)

        await manager.publish(restaurant_id, "table.status_changed", {"table_id": "t1"})

        await _wait_for(lambda: ws1.sent and ws2.sent)

        for ws in (ws1, ws2):
            message = json.loads(ws.sent[0])
            assert message["type"] == "table.status_changed"
            assert message["data"] == {"table_id": "t1"}

        # Rooms are isolated: the other restaurant's socket saw nothing.
        assert ws_other.sent == []
    finally:
        await manager.stop()


async def test_disconnected_sockets_are_pruned() -> None:
    manager = ConnectionManager()
    await manager.start()
    restaurant_id = uuid.uuid4()

    class BrokenWebSocket(StubWebSocket):
        async def send_text(self, text: str) -> None:
            raise RuntimeError("connection lost")

    healthy, broken = StubWebSocket(), BrokenWebSocket()
    try:
        await manager.connect(restaurant_id, healthy)
        await manager.connect(restaurant_id, broken)

        await manager.publish(restaurant_id, "ping", {})
        await _wait_for(lambda: healthy.sent)

        room = manager._rooms.get(channel_for(restaurant_id), set())
        assert broken not in room
        assert healthy in room
    finally:
        await manager.stop()


async def test_queue_event_publishes_only_on_flush(db_session: AsyncSession) -> None:
    """queue_event stores; publish_queued sends; discard_queued drops."""
    restaurant_id = uuid.uuid4()
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel_for(restaurant_id))
    try:
        queue_event(db_session, restaurant_id, "reservation.created", {"reservation_id": "r1"})

        # Nothing published yet (get one subscription-confirmation frame only).
        first = await pubsub.get_message(timeout=1.0)
        assert first is not None and first["type"] == "subscribe"
        assert await pubsub.get_message(timeout=0.3) is None

        await publish_queued(db_session)
        message = None

        async with asyncio.timeout(3):
            while message is None or message["type"] != "message":
                message = await pubsub.get_message(timeout=1.0)
        payload = json.loads(message["data"])
        assert payload["type"] == "reservation.created"

        # Queue is drained after publishing.
        await publish_queued(db_session)
        assert await pubsub.get_message(timeout=0.3) is None

        # Discard drops without publishing.
        queue_event(db_session, restaurant_id, "reservation.cancelled", {})
        discard_queued(db_session)
        await publish_queued(db_session)
        assert await pubsub.get_message(timeout=0.3) is None
    finally:
        await pubsub.aclose()
