# ADR 0003: Notification delivery behind a strategy interface

## Status
Accepted

## Context
The system needs to notify customers of reservation confirmations, reminders, cancellations, and updates. Real delivery (SMTP/SendGrid, SMS providers) requires external accounts and API keys that shouldn't be a hard requirement to run or evaluate the project locally, but the design should not preclude wiring up real delivery later.

## Decision
Define a `NotificationSender` abstract interface (`send(notification: Notification) -> None`) in `app/notifications/base.py`. Callers (Celery tasks in Phase 5) depend only on this interface, obtained through a DI factory (`get_notification_sender()`), never on a concrete implementation.

The initial and default implementation, `LoggedNotificationSender`, "delivers" a notification by writing a structured log entry and updating the `Notification` row's status — no external network calls. It satisfies the same interface a future `SmtpNotificationSender` or `SendGridNotificationSender` would.

## Consequences
- Swapping to real email/SMS delivery later is a configuration + DI factory change, with zero changes to service-layer call sites that enqueue notifications.
- The project is runnable end-to-end with no external notification provider account, while every notification is still fully observable via the `Notification` table and logs.
- The `Notification` table doubles as an audit trail/outbox regardless of which sender implementation is active.
