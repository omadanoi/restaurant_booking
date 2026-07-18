# Restaurant Reservation & Table Management Platform

A production-style full-stack reservation and table management system for restaurants, built to demonstrate backend engineering, systems design, and QA automation practices.

See [`docs/architecture.md`](docs/architecture.md) for the full architecture writeup and [`docs/adr/`](docs/adr/) for key design decisions.

## Status

**Phase 1 of 7** — database schema, migrations, and project scaffolding. See the roadmap in `docs/architecture.md` for what's next.

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
