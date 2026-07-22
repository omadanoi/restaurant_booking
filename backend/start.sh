#!/bin/sh
# Container entrypoint for managed hosts (Railway, Render, Fly...).
#
# Migrations run here rather than in a separate release step so a fresh
# deploy of a fresh database converges on its own. `alembic upgrade head`
# is a no-op once the schema is current, so restarts stay cheap.
set -e

echo "Applying database migrations..."
alembic upgrade head

# Opt-in demo content for a portfolio deployment. The seed script is
# idempotent, so leaving this on across restarts is harmless.
if [ "$SEED_DEMO_DATA" = "true" ]; then
  echo "Seeding demo data..."
  python -m scripts.seed
fi

# Hosts inject the port to bind; 8000 keeps local `docker run` working.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
