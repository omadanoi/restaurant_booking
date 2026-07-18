from functools import lru_cache

from app.core.config import get_settings
from app.notifications.base import NotificationSender
from app.notifications.logged import LoggedNotificationSender


@lru_cache
def get_notification_sender() -> NotificationSender:
    """DI seam for delivery strategies (ADR 0003).

    Adding a real provider later = new class + new branch here + setting
    change; zero changes anywhere else.
    """
    name = get_settings().NOTIFICATION_SENDER
    if name == "logged":
        return LoggedNotificationSender()
    raise ValueError(f"Unknown NOTIFICATION_SENDER: {name!r}")
