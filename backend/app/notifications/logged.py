from app.core.logging import get_logger
from app.models import Notification
from app.notifications.base import NotificationSender

logger = get_logger(__name__)


class LoggedNotificationSender(NotificationSender):
    """Self-contained default: "delivery" is a structured log line.

    Together with the Notification table (which records every notification
    and its status regardless of sender), this makes the whole notification
    pipeline observable without any external provider account.
    """

    def send(self, notification: Notification) -> None:
        logger.info(
            "notification_sent",
            extra={
                "extra_fields": {
                    "notification_id": str(notification.id),
                    "type": notification.type.value,
                    "channel": notification.channel.value,
                    "user_id": str(notification.user_id) if notification.user_id else None,
                    "payload": notification.payload,
                }
            },
        )
