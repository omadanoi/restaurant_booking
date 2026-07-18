import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    OverlappingReservationError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models import AuditLog, Notification, Reservation, Restaurant, Table, User
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    ReservationStatus,
    UserRole,
)
from app.realtime.events import queue_event
from app.repositories.reservation import ReservationRepository
from app.repositories.restaurant import RestaurantRepository
from app.repositories.table import TableRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate

logger = get_logger(__name__)

# Statuses a customer/staff may cancel from.
CANCELLABLE = (ReservationStatus.PENDING, ReservationStatus.CONFIRMED)

# Allowed staff-driven transitions.
STAFF_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.PENDING: {ReservationStatus.CONFIRMED, ReservationStatus.CANCELLED},
    ReservationStatus.CONFIRMED: {
        ReservationStatus.SEATED,
        ReservationStatus.CANCELLED,
        ReservationStatus.NO_SHOW,
    },
    ReservationStatus.SEATED: {ReservationStatus.COMPLETED},
}


class ReservationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.reservations = ReservationRepository(db)
        self.tables = TableRepository(db)
        self.restaurants = RestaurantRepository(db)

    # -- booking --------------------------------------------------------------

    async def create(self, customer: User, data: ReservationCreate) -> Reservation:
        """The concurrency-critical path (ADR 0002):

        1. Row-lock the table (FOR UPDATE) — concurrent bookings of the same
           table queue up behind this transaction.
        2. Validate (table active, capacity, opening hours, not in past).
        3. Explicit overlap pre-check — clean 409 for the common case.
        4. INSERT; the EXCLUDE constraint is the backstop for anything that
           slips through, translated to the same 409.
        """
        table = await self.tables.get_for_update(data.table_id)
        if table is None or not table.is_active:
            raise NotFoundError("Table not found.")

        restaurant = await self.restaurants.get(table.restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise NotFoundError("Restaurant not found.")

        self._validate_party_size(table, data.party_size)
        self._validate_not_in_past(data.start_time)
        await self._validate_within_opening_hours(restaurant, data.start_time, data.end_time)

        overlapping = await self.reservations.get_overlapping(
            table.id, data.start_time, data.end_time
        )
        if overlapping:
            raise OverlappingReservationError()

        try:
            reservation = await self.reservations.create(
                {
                    "restaurant_id": table.restaurant_id,
                    "table_id": table.id,
                    "customer_id": customer.id,
                    "start_time": data.start_time,
                    "end_time": data.end_time,
                    "party_size": data.party_size,
                    "special_requests": data.special_requests,
                    "status": ReservationStatus.CONFIRMED,
                }
            )
        except IntegrityError as exc:
            if "ex_reservations_no_overlap" in str(exc.orig):
                raise OverlappingReservationError() from exc
            raise

        await self._audit(customer, "reservation.created", reservation)
        self._queue_reservation_event("reservation.created", reservation)
        self._queue_notification(NotificationType.RESERVATION_CONFIRMED, reservation)
        logger.info(
            "reservation_created",
            extra={
                "extra_fields": {
                    "reservation_id": str(reservation.id),
                    "table_id": str(table.id),
                    "customer_id": str(customer.id),
                }
            },
        )
        return reservation

    async def modify(
        self, actor: User, reservation_id: uuid.UUID, data: ReservationUpdate
    ) -> Reservation:
        reservation = await self._get_owned_or_staff(actor, reservation_id)
        if reservation.status not in CANCELLABLE:
            raise ValidationError("Only pending or confirmed reservations can be modified.")

        new_start = data.start_time or reservation.start_time
        new_end = data.end_time or reservation.end_time
        if new_end <= new_start:
            raise ValidationError("end_time must be after start_time.")

        # Re-run the same locked overlap protocol as create().
        table = await self.tables.get_for_update(reservation.table_id)
        assert table is not None
        restaurant = await self.restaurants.get(table.restaurant_id)
        assert restaurant is not None

        if data.party_size is not None:
            self._validate_party_size(table, data.party_size)
        if data.start_time is not None or data.end_time is not None:
            self._validate_not_in_past(new_start)
            await self._validate_within_opening_hours(restaurant, new_start, new_end)
            overlapping = await self.reservations.get_overlapping(
                table.id, new_start, new_end, exclude_reservation_id=reservation.id
            )
            if overlapping:
                raise OverlappingReservationError()

        before = self._snapshot(reservation)
        try:
            reservation = await self.reservations.update(
                reservation,
                {
                    "start_time": new_start,
                    "end_time": new_end,
                    **({"party_size": data.party_size} if data.party_size is not None else {}),
                    **(
                        {"special_requests": data.special_requests}
                        if data.special_requests is not None
                        else {}
                    ),
                },
            )
        except IntegrityError as exc:
            if "ex_reservations_no_overlap" in str(exc.orig):
                raise OverlappingReservationError() from exc
            raise

        await self._audit(actor, "reservation.modified", reservation, before=before)
        self._queue_reservation_event("reservation.updated", reservation)
        # Update notices reuse the confirmation type with an event marker —
        # the enum stays small and the payload carries the nuance.
        self._queue_notification(
            NotificationType.RESERVATION_CONFIRMED, reservation, event="updated"
        )
        return reservation

    async def cancel(self, actor: User, reservation_id: uuid.UUID) -> Reservation:
        reservation = await self._get_owned_or_staff(actor, reservation_id)
        if reservation.status not in CANCELLABLE:
            raise ValidationError("This reservation cannot be cancelled.")

        before = self._snapshot(reservation)
        reservation = await self.reservations.update(
            reservation,
            {"status": ReservationStatus.CANCELLED, "cancelled_at": datetime.now(timezone.utc)},
        )
        await self._audit(actor, "reservation.cancelled", reservation, before=before)
        self._queue_reservation_event("reservation.cancelled", reservation)
        self._queue_notification(NotificationType.RESERVATION_CANCELLED, reservation)
        logger.info(
            "reservation_cancelled",
            extra={"extra_fields": {"reservation_id": str(reservation.id)}},
        )
        return reservation

    async def change_status(
        self, staff: User, reservation_id: uuid.UUID, new_status: ReservationStatus
    ) -> Reservation:
        """Staff-driven lifecycle transitions (seat, complete, no-show...)."""
        reservation = await self.reservations.get(reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation not found.")

        allowed = STAFF_TRANSITIONS.get(reservation.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot move a {reservation.status.value} reservation to {new_status.value}."
            )

        before = self._snapshot(reservation)
        updates: dict = {"status": new_status}
        if new_status == ReservationStatus.CONFIRMED:
            updates["confirmed_by"] = staff.id
        if new_status == ReservationStatus.CANCELLED:
            updates["cancelled_at"] = datetime.now(timezone.utc)
        reservation = await self.reservations.update(reservation, updates)
        await self._audit(staff, f"reservation.{new_status.value}", reservation, before=before)
        self._queue_reservation_event("reservation.updated", reservation)
        return reservation

    # -- queries --------------------------------------------------------------

    async def get_for_actor(self, actor: User, reservation_id: uuid.UUID) -> Reservation:
        return await self._get_owned_or_staff(actor, reservation_id)

    async def find_available_tables(
        self,
        restaurant_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        party_size: int,
        *,
        floor_id: uuid.UUID | None = None,
        indoor: bool | None = None,
        accessible: bool | None = None,
    ) -> list[Table]:
        """Availability search: active tables with adequate capacity that
        have no overlapping active reservation in the window.
        """
        if end_time <= start_time:
            raise ValidationError("end_time must be after start_time.")
        restaurant = await self.restaurants.get(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise NotFoundError("Restaurant not found.")

        tables = await self.tables.list_for_restaurant(restaurant_id, floor_id=floor_id)
        taken = await self.reservations.reserved_table_ids(restaurant_id, start_time, end_time)

        def fits(t: Table) -> bool:
            if t.id in taken or t.capacity < party_size:
                return False
            if t.min_capacity is not None and party_size < t.min_capacity:
                return False
            if indoor is not None and t.is_indoor != indoor:
                return False
            if accessible is not None and t.is_accessible != accessible:
                return False
            return True

        return [t for t in tables if fits(t)]

    # -- internals ------------------------------------------------------------

    async def _get_owned_or_staff(self, actor: User, reservation_id: uuid.UUID) -> Reservation:
        from app.core.permissions import check_restaurant_staff

        reservation = await self.reservations.get(reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation not found.")
        if reservation.customer_id == actor.id:
            return reservation
        # Not the owner — must be staff of the restaurant (or admin).
        try:
            await check_restaurant_staff(self.db, actor, reservation.restaurant_id)
        except PermissionDeniedError:
            # Don't leak existence of other people's reservations.
            raise NotFoundError("Reservation not found.")
        return reservation

    def _validate_party_size(self, table: Table, party_size: int) -> None:
        if party_size > table.capacity:
            raise ValidationError(
                f"Party of {party_size} exceeds table capacity of {table.capacity}."
            )
        if table.min_capacity is not None and party_size < table.min_capacity:
            raise ValidationError(
                f"This table requires a party of at least {table.min_capacity}."
            )

    def _validate_not_in_past(self, start_time: datetime) -> None:
        if start_time <= datetime.now(timezone.utc):
            raise ValidationError("Reservations must start in the future.")

    async def _validate_within_opening_hours(
        self, restaurant: Restaurant, start_time: datetime, end_time: datetime
    ) -> None:
        """Checks the window against the restaurant's local-time schedule.

        Overnight windows (closing past midnight) and multi-day reservations
        are out of scope: the window must fall within a single local day's
        open hours.
        """
        tz = ZoneInfo(restaurant.timezone)
        local_start = start_time.astimezone(tz)
        local_end = end_time.astimezone(tz)

        if local_start.date() != local_end.date():
            raise ValidationError("Reservations must start and end on the same day.")

        holiday = await self.restaurants.get_holiday_for_date(restaurant.id, local_start.date())
        if holiday is not None:
            if holiday.is_closed:
                raise ValidationError("The restaurant is closed on this date.")
            opens, closes = holiday.opens_at, holiday.closes_at
        else:
            hours = await self.restaurants.get_opening_hours(restaurant.id)
            todays = next(
                (h for h in hours if h.day_of_week == local_start.weekday()), None
            )
            if todays is None:
                # No schedule configured — treat as always open (dev-friendly).
                return
            if todays.is_closed:
                raise ValidationError("The restaurant is closed on this day.")
            opens, closes = todays.opens_at, todays.closes_at

        if opens is None or closes is None:
            return
        if local_start.time() < opens or local_end.time() > closes:
            raise ValidationError(
                f"Reservation must be within opening hours ({opens}–{closes} local time)."
            )

    def _queue_notification(
        self, type_: NotificationType, reservation: Reservation, *, event: str | None = None
    ) -> None:
        """Inserts a pending Notification in the SAME transaction as the
        domain change (transactional outbox): if the booking rolls back, no
        notification exists; delivery happens via the Celery dispatcher.
        """
        payload = {
            "reservation_id": str(reservation.id),
            "start_time": reservation.start_time.isoformat(),
            "end_time": reservation.end_time.isoformat(),
            "party_size": reservation.party_size,
            "status": reservation.status.value,
        }
        if event is not None:
            payload["event"] = event
        self.db.add(
            Notification(
                user_id=reservation.customer_id,
                restaurant_id=reservation.restaurant_id,
                reservation_id=reservation.id,
                type=type_,
                channel=NotificationChannel.IN_APP,
                payload=payload,
                status=NotificationStatus.PENDING,
            )
        )

    def _queue_reservation_event(self, event_type: str, reservation: Reservation) -> None:
        """No personal data in the payload — see app/realtime/events.py."""
        queue_event(
            self.db,
            reservation.restaurant_id,
            event_type,
            {
                "reservation_id": str(reservation.id),
                "table_id": str(reservation.table_id),
                "start_time": reservation.start_time.isoformat(),
                "end_time": reservation.end_time.isoformat(),
                "status": reservation.status.value,
            },
        )

    def _snapshot(self, reservation: Reservation) -> dict:
        return {
            "start_time": reservation.start_time.isoformat(),
            "end_time": reservation.end_time.isoformat(),
            "party_size": reservation.party_size,
            "status": reservation.status.value,
        }

    async def _audit(
        self, actor: User, action: str, reservation: Reservation, *, before: dict | None = None
    ) -> None:
        self.db.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                entity_type="reservation",
                entity_id=reservation.id,
                before=before,
                after=self._snapshot(reservation),
            )
        )
        await self.db.flush()
