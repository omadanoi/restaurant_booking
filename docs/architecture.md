# Architecture

## Overview

The platform serves four roles — Customer, Waiter, Manager, Administrator — through a single FastAPI backend and (from Phase 6) a React frontend. The system centers on two hard engineering problems: representing a restaurant's floor layout as live, editable data (not a static image), and guaranteeing a table can never be double-booked even under concurrent requests.

## Layered backend architecture

```
Router (app/api)  ->  Service (app/services)  ->  Repository (app/repositories)  ->  Database
```

- **Routers** are thin: request/response schema validation, auth/RBAC dependencies, and a single call into a service method. No business logic lives here.
- **Services** hold use-case logic (booking rules, capacity checks, audit logging, notification dispatch) and are plain Python classes constructed via FastAPI dependency injection, so they're unit-testable without an HTTP layer. Services raise domain exceptions, never `HTTPException`.
- **Repositories** are the only layer that touches SQLAlchemy sessions directly. They never commit — the request-scoped session commits once, at the end of the request, so a use-case spanning multiple repositories is one atomic transaction.
- **Schemas** (Pydantic v2 DTOs) sit only at the router boundary; internal layers pass ORM models or plain Python values.

Domain exceptions (`app/core/exceptions.py`) are translated to HTTP responses by a single global exception handler registered in `app/main.py`, keeping error-to-status-code mapping in one place.

## Data model

See the ERD implied by `backend/app/models/`. Key entities: `User`, `Restaurant`, `Floor`, `Table`, `Reservation`, `TableStatusLog`, `Notification`, `AuditLog`, `OpeningHours`, `Holiday`, `EmployeeRestaurant`.

Two scoping concerns are deliberately separate:
- `User.role` — what kind of actions an account can perform in general (Admin is global).
- `EmployeeRestaurant` — which specific restaurant(s) a Waiter/Manager is authorized to act on.

## Concurrency: preventing double-booking

Overlapping reservations for the same table are prevented at the database level with a PostgreSQL `EXCLUDE` constraint (requires the `btree_gist` extension):

```sql
ALTER TABLE reservations
  ADD CONSTRAINT ex_reservations_no_overlap
  EXCLUDE USING gist (
    table_id WITH =,
    tstzrange(start_time, end_time, '[)') WITH &&
  ) WHERE (status NOT IN ('cancelled', 'no_show'));
```

This is a structural guarantee — it holds regardless of how many processes or code paths write to the table. The service layer (Phase 3) adds defense-in-depth on top: it takes a row lock (`SELECT ... FOR UPDATE`) on the table before checking for overlaps, so well-behaved callers get a clean `409 Conflict` instead of a raw constraint-violation error; the constraint remains the backstop for anything that slips past that check. See [ADR 0002](adr/0002-reservation-overlap-exclusion-constraint.md).

Because GiST exclusion constraints and `tstzrange` aren't available in SQLite, the test suite runs against a real PostgreSQL database rather than an in-memory substitute.

## Real-time updates (Phase 4)

Table status and reservation changes are broadcast over WebSockets, scoped per restaurant. Broadcasts are routed through Redis pub/sub rather than an in-process connection registry, so the design already supports running multiple backend workers without rework.

## Notifications (Phase 5)

Notifications (confirmations, reminders, cancellations) are dispatched via Celery background tasks against a `NotificationSender` interface. The initial implementation logs to the `Notification` table and structured logs only; a real email/SMS provider can be substituted later behind the same interface with no changes to calling code. See [ADR 0003](adr/0003-notification-strategy-pattern.md).

## Roadmap

1. **DB models & migrations** (this phase)
2. **Auth** — JWT access/refresh tokens, RBAC
3. **Core domain APIs** — restaurants, floors, tables, reservations, booking flow
4. **Real-time layer** — WebSockets over Redis pub/sub
5. **Notifications** — Celery + Redis background jobs
6. **Frontend** — React + TypeScript + Vite, role-aware UIs, drag-and-drop floor editor
7. **Testing & CI/CD** — full test pyramid, Playwright E2E, GitHub Actions, full Docker Compose stack
