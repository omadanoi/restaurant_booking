from abc import ABC, abstractmethod

from app.models import Notification


class NotificationSender(ABC):
    """Delivery strategy (ADR 0003). Implementations perform the actual
    delivery for one notification and raise on failure; they do NOT touch
    the notification's DB status — the dispatch task owns that lifecycle.
    """

    @abstractmethod
    def send(self, notification: Notification) -> None:
        ...
