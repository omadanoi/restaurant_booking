"""Notification background jobs.

Design: the Notification table is a transactional outbox. Services insert
`pending` rows inside the same transaction as the domain change (so a
rolled-back booking never notifies anyone), and `dispatch_pending_notifications`
delivers them via the configured NotificationSender. Each Celery task is a
thin wrapper around a testable plain function that takes a Session.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.sync_session import SyncSessionLocal
from app.models import Notification, RefreshToken, Reservation
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    ReservationStatus,
)
from app.notifications.base import NotificationSender
from app.notifications.provider import get_notification_sender
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


# -- core logic (plain functions, unit-testable with any Session) -------------


def dispatch_pending(session: Session, sender: NotificationSender, limit: int = 100) -> int:
    """Delivers up to `limit` pending notifications; returns how many sent."""
    pending = (
        session.execute(
            select(Notification)
            .where(Notification.status == NotificationStatus.PENDING)
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)  # safe with concurrent workers
        )
        .scalars()
        .all()
    )
    sent = 0
    for notification in pending:
        try:
            sender.send(notification)
        except Exception as exc:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(exc)[:2000]
            logger.exception(
                "notification_send_failed",
                extra={"extra_fields": {"notification_id": str(notification.id)}},
            )
        else:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(UTC)
            sent += 1
    session.flush()
    return sent


def schedule_reminders(session: Session, *, now: datetime | None = None) -> int:
    """Creates pending reminder notifications for confirmed reservations
    starting within REMINDER_LEAD_HOURS. Idempotent: a reservation gets at
    most one reminder (checked via existing reminder rows).
    """
    now = now or datetime.now(UTC)
    horizon = now + timedelta(hours=get_settings().REMINDER_LEAD_HOURS)

    already_reminded = select(Notification.reservation_id).where(
        Notification.type == NotificationType.RESERVATION_REMINDER,
        Notification.reservation_id.is_not(None),
    )
    due = (
        session.execute(
            select(Reservation).where(
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.start_time > now,
                Reservation.start_time <= horizon,
                Reservation.id.not_in(already_reminded),
            )
        )
        .scalars()
        .all()
    )
    for reservation in due:
        session.add(
            Notification(
                user_id=reservation.customer_id,
                restaurant_id=reservation.restaurant_id,
                reservation_id=reservation.id,
                type=NotificationType.RESERVATION_REMINDER,
                channel=NotificationChannel.IN_APP,
                payload={
                    "reservation_id": str(reservation.id),
                    "start_time": reservation.start_time.isoformat(),
                    "end_time": reservation.end_time.isoformat(),
                    "party_size": reservation.party_size,
                },
                status=NotificationStatus.PENDING,
            )
        )
    session.flush()
    return len(due)


def cleanup_refresh_tokens(session: Session, *, now: datetime | None = None) -> int:
    """Deletes refresh tokens that expired (or were revoked) over 30 days
    ago — they can never be used again and only accumulate.
    """
    cutoff = (now or datetime.now(UTC)) - timedelta(days=30)
    result = session.execute(
        delete(RefreshToken).where(
            or_(RefreshToken.expires_at < cutoff, RefreshToken.revoked_at < cutoff)
        )
    )
    return result.rowcount


# -- celery task wrappers -----------------------------------------------------


@celery_app.task
def dispatch_pending_notifications() -> int:
    with SyncSessionLocal() as session:
        sent = dispatch_pending(session, get_notification_sender())
        session.commit()
    if sent:
        logger.info("notifications_dispatched", extra={"extra_fields": {"count": sent}})
    return sent


@celery_app.task
def schedule_reservation_reminders() -> int:
    with SyncSessionLocal() as session:
        created = schedule_reminders(session)
        session.commit()
    if created:
        logger.info("reminders_scheduled", extra={"extra_fields": {"count": created}})
    return created


@celery_app.task
def cleanup_expired_refresh_tokens() -> int:
    with SyncSessionLocal() as session:
        removed = cleanup_refresh_tokens(session)
        session.commit()
    if removed:
        logger.info("refresh_tokens_cleaned", extra={"extra_fields": {"count": removed}})
    return removed
