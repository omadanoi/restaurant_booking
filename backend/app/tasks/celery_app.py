from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "restaurant_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # The outbox dispatcher makes delivery at-least-once even if a direct
    # enqueue is lost, so retries can stay modest.
    task_acks_late=True,
    beat_schedule={
        "dispatch-pending-notifications": {
            "task": "app.tasks.notification_tasks.dispatch_pending_notifications",
            "schedule": 30.0,  # seconds
        },
        "schedule-reservation-reminders": {
            "task": "app.tasks.notification_tasks.schedule_reservation_reminders",
            "schedule": 300.0,  # every 5 minutes
        },
        "cleanup-expired-refresh-tokens": {
            "task": "app.tasks.notification_tasks.cleanup_expired_refresh_tokens",
            "schedule": 24 * 3600.0,  # daily
        },
    },
)
