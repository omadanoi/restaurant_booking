import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models import Restaurant, User
from app.realtime.manager import manager

router = APIRouter(tags=["realtime"])

logger = get_logger(__name__)


@router.websocket("/ws/restaurants/{restaurant_id}")
async def restaurant_events(
    websocket: WebSocket,
    restaurant_id: uuid.UUID,
    token: str = Query(),
) -> None:
    """Live event stream for one restaurant (table status, reservations).

    Browsers can't set an Authorization header on WebSocket connections,
    so the access token is passed as a query parameter. Event payloads
    carry no personal data (see app/realtime/events.py), so any
    authenticated user may subscribe — staff dashboards and customer
    floor views use the same stream.
    """
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (AuthenticationError, KeyError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    # WebSockets live outside the request-scoped get_db dependency; use a
    # short-lived session just for the auth checks.
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        restaurant = await db.get(Restaurant, restaurant_id)

    if user is None or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user")
        return
    if restaurant is None or not restaurant.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unknown restaurant")
        return

    await manager.connect(restaurant_id, websocket)
    logger.info(
        "ws_connected",
        extra={"extra_fields": {"user_id": str(user_id), "restaurant_id": str(restaurant_id)}},
    )
    try:
        # Server-push only: we ignore inbound frames but must keep reading
        # so disconnects are noticed promptly.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(restaurant_id, websocket)
        logger.info(
            "ws_disconnected",
            extra={"extra_fields": {"user_id": str(user_id), "restaurant_id": str(restaurant_id)}},
        )
