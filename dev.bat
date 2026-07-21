@echo off
rem Starts the full dev environment in separate windows.
rem Postgres + Redis must already be running (they're Windows services on this
rem machine; elsewhere: docker compose up -d db redis from infra/).

start "backend :8000" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload"
start "frontend :5173" cmd /k "cd /d %~dp0frontend && npm run dev"

rem Optional: uncomment for notification delivery
rem start "celery worker" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && celery -A app.tasks.celery_app worker -P solo -l info"
rem start "celery beat" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && celery -A app.tasks.celery_app beat -l info"

echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173
