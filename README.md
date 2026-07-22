# Restaurant Reservation & Table Management Platform

[![Backend CI](https://github.com/omadanoi/restaurant_booking/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/omadanoi/restaurant_booking/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/omadanoi/restaurant_booking/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/omadanoi/restaurant_booking/actions/workflows/frontend-ci.yml)
[![E2E](https://github.com/omadanoi/restaurant_booking/actions/workflows/e2e.yml/badge.svg)](https://github.com/omadanoi/restaurant_booking/actions/workflows/e2e.yml)

A production-style full-stack reservation system: customers book specific tables on an interactive floor plan, staff manage the floor in real time, and the database makes double-booking structurally impossible.

## Features

**Customers** — browse restaurants, search availability by date/time/party size (with indoor/outdoor and accessibility filters), pick a table on a live floor plan rendered from database geometry, book it, modify or cancel later, and get confirmations and reminders in a notification feed.

**Waiters** — a live dashboard where the floor plan updates over WebSockets the moment anything changes: seat walk-ins, mark tables as cleaning or free, and work the day's reservation book (confirm → seat → complete / no-show, with illegal transitions rejected).

**Managers** — everything waiters have, plus a drag-and-drop floor editor (move, rotate, add, remove tables; every change persists to the database and broadcasts live) and per-day opening hours and holiday configuration.

**Admins** — create and suspend restaurants, manage users, global access across all restaurants.

## Engineering highlights

- **Double-booking is impossible at the database level**: a PostgreSQL `EXCLUDE` constraint over `(table_id, tstzrange(start, end))` guarantees no two active reservations overlap, regardless of application bugs or concurrent writers. The service layer adds `SELECT ... FOR UPDATE` row-locking on top for clean `409` errors instead of raw constraint violations. Proven by 2-way and 5-way concurrent race tests. ([ADR 0002](docs/adr/0002-reservation-overlap-exclusion-constraint.md))
- **JWT auth with refresh-token rotation and reuse detection**: refresh tokens are stored only as SHA-256 hashes and rotate on every use; replaying a rotated-out token revokes every active session for that user (stolen-token response).
- **Transactional outbox for notifications**: notification rows are inserted in the same transaction as the booking, so a rollback can never notify anyone; Celery workers deliver them (`FOR UPDATE SKIP LOCKED` prevents double-sends). Delivery is behind a strategy interface — swapping the logged default for real email/SMS is a one-setting change. ([ADR 0003](docs/adr/0003-notification-strategy-pattern.md))
- **Real-time updates route through Redis pub/sub**, not in-process state, so WebSocket fan-out already works with multiple server workers. Events publish only after the DB transaction commits.
- **Layered architecture**: thin routers → services (business logic, domain exceptions) → repositories (data access, never commit) → one atomic transaction per request. RBAC is two-dimensional: global roles plus per-restaurant staff assignments.

Full writeup: [`docs/architecture.md`](docs/architecture.md) · decisions: [`docs/adr/`](docs/adr/)

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Data | PostgreSQL 16 (`btree_gist`), Redis 7 |
| Background jobs | Celery (worker + beat) |
| Realtime | WebSockets over Redis pub/sub |
| Frontend | React 18, TypeScript, Vite, custom SVG floor renderer |
| Testing | pytest (79 backend tests), Playwright (9 E2E), ruff |
| CI/CD | GitHub Actions, Docker Compose |

## Getting started

### Option A — Docker (one command)

```bash
cd infra
docker compose up --build
```

Frontend at http://localhost:5173, API docs at http://localhost:8000/docs. Seed demo data once the stack is up:

```bash
docker compose exec backend python -m scripts.seed
```

### Option B — run locally

Requires Python 3.11+, Node 20+, PostgreSQL 16+ (with the `btree_gist` extension available), and Redis (on Windows, [Memurai](https://www.memurai.com/) works well).

```bash
# 1. Databases (skip if using `docker compose up -d db redis` from infra/)
#    Create restaurant_platform and restaurant_platform_test, and enable
#    btree_gist in both:  CREATE EXTENSION IF NOT EXISTS btree_gist;

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
copy .env.example .env            # then set your DB credentials in .env
alembic upgrade head
python -m scripts.seed            # demo accounts + demo restaurant
uvicorn app.main:app --reload

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Background jobs — optional, for notification delivery (two more terminals)
celery -A app.tasks.celery_app worker -P solo -l info    # -P solo required on Windows
celery -A app.tasks.celery_app beat -l info
```

### Demo accounts

All seeded with password `Password123`:

| Account | Role | Try this |
|---|---|---|
| `customer@demo.com` | Customer | Book a table on the floor plan; try booking the same slot twice |
| `waiter@demo.com` | Waiter | Watch the floor update live while a customer books in another window |
| `manager@demo.com` | Manager | Drag tables around in the floor editor; edit opening hours |
| `admin@demo.com` | Admin | Create a restaurant; view all users |

## Testing

```bash
cd backend && pytest              # 85 tests: unit, API, integration
cd backend && ruff check .        # lint
cd frontend && npx playwright test  # 9 browser E2E tests (needs seeded data)
```

Backend tests run against a real PostgreSQL test database (the overlap constraint needs real `btree_gist`), and include DB-level constraint tests plus true concurrent-booking races fired from independent connections. E2E covers registration, login failures, the full book-and-cancel flow, opening-hours rejection, role guards, drag-and-drop persistence across reload, and a live WebSocket update between two sessions. All of it runs in GitHub Actions on every push and pull request.

## Deployment

Both services ship as Dockerfiles that bind the host-assigned `$PORT`, and the backend applies its own migrations on boot, so the stack deploys to any container host. [`docs/deploy.md`](docs/deploy.md) is a step-by-step walkthrough for Railway (API + SPA + Postgres + Redis, managed TLS so the realtime socket upgrades to `wss://`), with notes for Render, Fly.io and a plain VPS.

## Repository layout

```
backend/    FastAPI app — clean architecture: api → services → repositories → db
  app/      models, schemas, services, repositories, realtime, tasks, notifications
  alembic/  migrations (incl. the EXCLUDE constraint)
  tests/    unit / api / integration
  scripts/  seed.py — demo data
frontend/   React + TypeScript SPA, Playwright E2E in e2e/
infra/      Docker Compose (full stack) + Postgres init
docs/       architecture.md, deploy.md + ADRs
.github/    CI workflows (backend, frontend, E2E)
```
