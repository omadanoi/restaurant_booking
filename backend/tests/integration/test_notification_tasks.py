"""Notification task logic, tested through the same sync Session type the
Celery workers use — each test runs in a rolled-back transaction on the
test database, so no broker or worker is needed.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.models import (
    Floor,
    Notification,
    RefreshToken,
    Reservation,
    Restaurant,
    Table,
    User,
)
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    ReservationStatus,
    TableShape,
    UserRole,
)
from app.notifications.base import NotificationSender
from app.notifications.logged import LoggedNotificationSender
from app.tasks.notification_tasks import (
    cleanup_refresh_tokens,
    dispatch_pending,
    schedule_reminders,
)
from tests.conftest import TEST_SYNC_DATABASE_URL


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(TEST_SYNC_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Transaction-per-test, rolled back afterwards (sync flavor of the
    async db_session fixture).
    """
    connection = sync_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _seed_reservation(session: Session, *, starts_in: timedelta) -> Reservation:
    marker = uuid.uuid4().hex[:8]
    restaurant = Restaurant(
        name=f"NotifTest-{marker}", address="1 N St", city="N", country="US", timezone="UTC"
    )
    session.add(restaurant)
    session.flush()
    floor = Floor(restaurant_id=restaurant.id, name="Main", level=0)
    session.add(floor)
    session.flush()
    table = Table(
        restaurant_id=restaurant.id,
        floor_id=floor.id,
        table_number=f"N-{marker}",
        shape=TableShape.SQUARE,
        capacity=4,
    )
    customer = User(
        email=f"notif-{marker}@test.com",
        hashed_password=hash_password("irrelevant"),
        full_name="Notif Customer",
        role=UserRole.CUSTOMER,
    )
    session.add_all([table, customer])
    session.flush()

    start = datetime.now(UTC) + starts_in
    reservation = Reservation(
        restaurant_id=restaurant.id,
        table_id=table.id,
        customer_id=customer.id,
        start_time=start,
        end_time=start + timedelta(hours=2),
        party_size=2,
        status=ReservationStatus.CONFIRMED,
    )
    session.add(reservation)
    session.flush()
    return reservation


def _pending_notification(session: Session, reservation: Reservation) -> Notification:
    notification = Notification(
        user_id=reservation.customer_id,
        restaurant_id=reservation.restaurant_id,
        reservation_id=reservation.id,
        type=NotificationType.RESERVATION_CONFIRMED,
        channel=NotificationChannel.IN_APP,
        payload={"reservation_id": str(reservation.id)},
        status=NotificationStatus.PENDING,
    )
    session.add(notification)
    session.flush()
    return notification


def test_dispatch_marks_sent(sync_session: Session) -> None:
    reservation = _seed_reservation(sync_session, starts_in=timedelta(days=2))
    notification = _pending_notification(sync_session, reservation)

    sent = dispatch_pending(sync_session, LoggedNotificationSender())

    assert sent == 1
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None

    # Second run: nothing pending anymore.
    assert dispatch_pending(sync_session, LoggedNotificationSender()) == 0


def test_dispatch_marks_failed_on_sender_error(sync_session: Session) -> None:
    reservation = _seed_reservation(sync_session, starts_in=timedelta(days=2))
    notification = _pending_notification(sync_session, reservation)

    class ExplodingSender(NotificationSender):
        def send(self, notification: Notification) -> None:
            raise RuntimeError("smtp exploded")

    sent = dispatch_pending(sync_session, ExplodingSender())

    assert sent == 0
    assert notification.status == NotificationStatus.FAILED
    assert "smtp exploded" in notification.error_message


def test_reminders_created_once_within_lead_window(sync_session: Session) -> None:
    soon = _seed_reservation(sync_session, starts_in=timedelta(hours=3))
    _far = _seed_reservation(sync_session, starts_in=timedelta(days=10))

    created = schedule_reminders(sync_session)
    assert created == 1

    reminder = sync_session.execute(
        select(Notification).where(
            Notification.reservation_id == soon.id,
            Notification.type == NotificationType.RESERVATION_REMINDER,
        )
    ).scalar_one()
    assert reminder.status == NotificationStatus.PENDING
    assert reminder.user_id == soon.customer_id

    # Idempotent: running again creates no duplicates.
    assert schedule_reminders(sync_session) == 0


def test_no_reminder_for_cancelled_reservation(sync_session: Session) -> None:
    reservation = _seed_reservation(sync_session, starts_in=timedelta(hours=3))
    reservation.status = ReservationStatus.CANCELLED
    sync_session.flush()

    assert schedule_reminders(sync_session) == 0


def test_cleanup_removes_only_stale_tokens(sync_session: Session) -> None:
    marker = uuid.uuid4().hex[:8]
    user = User(
        email=f"tok-{marker}@test.com",
        hashed_password=hash_password("irrelevant"),
        full_name="Token User",
        role=UserRole.CUSTOMER,
    )
    sync_session.add(user)
    sync_session.flush()

    now = datetime.now(UTC)

    def token(suffix: str, *, expires: datetime, revoked: datetime | None = None) -> RefreshToken:
        t = RefreshToken(
            user_id=user.id,
            token_hash=f"{marker}-{suffix}".ljust(64, "0"),
            expires_at=expires,
            revoked_at=revoked,
        )
        sync_session.add(t)
        return t

    stale_expired = token("stale", expires=now - timedelta(days=40))
    stale_revoked = token(
        "revoked", expires=now + timedelta(days=1), revoked=now - timedelta(days=35)
    )
    active = token("active", expires=now + timedelta(days=7))
    recently_expired = token("recent", expires=now - timedelta(days=2))
    sync_session.flush()

    removed = cleanup_refresh_tokens(sync_session)
    assert removed == 2

    remaining = set(
        sync_session.execute(
            select(RefreshToken.token_hash).where(RefreshToken.user_id == user.id)
        ).scalars()
    )
    assert active.token_hash in remaining
    assert recently_expired.token_hash in remaining
    assert stale_expired.token_hash not in remaining
    assert stale_revoked.token_hash not in remaining
