# Restaurant Reservation & Table Management Platform

[![Backend CI](https://github.com/omadanoi/restaurant_booking/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/omadanoi/restaurant_booking/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/omadanoi/restaurant_booking/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/omadanoi/restaurant_booking/actions/workflows/frontend-ci.yml)
[![E2E](https://github.com/omadanoi/restaurant_booking/actions/workflows/e2e.yml/badge.svg)](https://github.com/omadanoi/restaurant_booking/actions/workflows/e2e.yml)

A production-style full-stack reservation and table management system for restaurants, built to demonstrate backend engineering, systems design, and QA automation practices.

See [`docs/architecture.md`](docs/architecture.md) for the full architecture writeup and [`docs/adr/`](docs/adr/) for key design decisions.

## Testing

- **Backend** (`cd backend && pytest`): 79 tests — unit, API, and integration, including DB-level EXCLUDE-constraint tests and true concurrent-booking races (2-way and 5-way) against real Postgres.
- **E2E** (`cd frontend && npx playwright test`): 9 browser tests covering registration, login failures, the full booking flow on the floor plan, opening-hours rejection, role guards, manager drag-and-drop persistence, and a live WebSocket update across two sessions. Requires the seeded demo data (`python -m scripts.seed`).
- **Lint**: `ruff check .` in `backend/`.

All three run in GitHub Actions on every push and pull request.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16, Redis 7
- **Frontend** (Phase 6+): React, TypeScript, Vite
- **Background jobs** (Phase 5+): Celery + Redis
- **Testing**: pytest (unit/integration/API), Playwright (E2E, Phase 7+)

## Quickstart (Phase 1)

Requires Python 3.11+ and either Docker Desktop or a local PostgreSQL 16+ server (with the `btree_gist` extension available) plus Redis.

```bash
# 1. Start Postgres + Redis
cd infra
docker compose up -d

# 2. Set up the backend
cd ../backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements-dev.txt
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 3. Apply migrations
alembic upgrade head

# 4. Run the API
uvicorn app.main:app --reload

# 5. Run tests
pytest
```

The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### Frontend (React + TypeScript + Vite)

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and sign in with a demo account (see `backend/scripts/seed.py`; password `Password123`): `customer@demo.com` books tables on the interactive floor plan, `waiter@demo.com` gets the live staff dashboard, `manager@demo.com` additionally gets the drag-and-drop floor editor, and `admin@demo.com` gets the admin panel.

### Background jobs (notifications)

Notifications use a transactional outbox: bookings insert `pending` rows, and Celery delivers them. Run the worker and scheduler in two extra terminals (from `backend/`, venv active):

```bash
celery -A app.tasks.celery_app worker -P solo -l info   # -P solo required on Windows
celery -A app.tasks.celery_app beat -l info
```

The default `NOTIFICATION_SENDER=logged` "delivers" by writing structured logs and updating the notification row — swap in a real email/SMS sender later via that setting alone (see `docs/adr/0003-notification-strategy-pattern.md`). Check your feed at `GET /api/v1/notifications/me`.

## Repository Layout

```
backend/     FastAPI application (clean architecture: api -> services -> repositories -> db)
frontend/    React + TypeScript client (Phase 6+)
infra/       Docker Compose and infrastructure config
docs/        Architecture notes and ADRs
```
