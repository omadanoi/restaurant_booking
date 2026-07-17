"""Post-commit event queue (a lightweight transactional-outbox pattern).

Services never publish directly — they queue events on the session via
`queue_event()`, and `get_db` publishes the queue only after the
transaction commits successfully. A rolled-back booking therefore never
broadcasts a phantom "reservation.created".

Event payloads are intentionally free of personal data (no customer ids,
names, or contact info): the same stream serves staff dashboards and
customer-facing floor views.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.realtime.manager import manager

logger = get_logger(__name__)

_QUEUE_KEY = "pending_realtime_events"


def queue_event(
    db: AsyncSession,
    restaurant_id: uuid.UUID | str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    db.info.setdefault(_QUEUE_KEY, []).append((str(restaurant_id), event_type, data))


async def publish_queued(db: AsyncSession) -> None:
    """Called by get_db after a successful commit."""
    events = db.info.pop(_QUEUE_KEY, [])
    for restaurant_id, event_type, data in events:
        try:
            await manager.publish(restaurant_id, event_type, data)
        except Exception:
            # Realtime is best-effort: a Redis hiccup must not fail the
            # request whose transaction already committed.
            logger.exception(
                "event_publish_failed",
                extra={"extra_fields": {"event_type": event_type}},
            )


def discard_queued(db: AsyncSession) -> None:
    db.info.pop(_QUEUE_KEY, None)
