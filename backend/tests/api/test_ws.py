"""WebSocket endpoint auth tests.

Uses Starlette's sync TestClient (httpx's AsyncClient has no websocket
support). Only rejection paths are tested here — they close the socket
before any database access, so no test-DB wiring is needed. The happy
path (connect + receive a live event) is covered end-to-end by the Phase 7
system tests and manual smoke testing.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.main import app

settings = get_settings()


def test_ws_rejects_garbage_token() -> None:
    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(
            f"{settings.API_V1_STR}/ws/restaurants/{uuid.uuid4()}?token=garbage"
        ) as ws,
    ):
        ws.receive_text()
    assert exc_info.value.code == 1008


def test_ws_requires_token_param() -> None:
    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"{settings.API_V1_STR}/ws/restaurants/{uuid.uuid4()}") as ws,
    ):
        ws.receive_text()
