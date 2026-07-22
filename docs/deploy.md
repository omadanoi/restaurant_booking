# Deploying

This walks through putting the app on **Railway** — one dashboard for all four
pieces (API, static frontend, PostgreSQL, Redis), managed HTTPS so the realtime
WebSocket upgrades to `wss://` without extra work, and no cold starts on the
free-ish tier. Budget about **$5/month** for a demo-traffic deployment.

Everything below is also enough to adapt to Render, Fly.io or a plain VPS —
the app only needs a Postgres URL, a Redis URL, and a port to bind.

## What the platform needs from you

| Requirement | Where it is handled |
| --- | --- |
| Bind the host-assigned `$PORT` | `backend/start.sh`, `frontend/nginx.conf.template` |
| Run migrations on deploy | `alembic upgrade head` in `backend/start.sh` |
| `btree_gist` extension | Created by migration `0001` (needed by the no-double-booking constraint) |
| Driver-specific DSNs | Derived from one plain `postgresql://` URL in `app/core/config.py` |

## 1. Push to GitHub

Railway deploys from a repository, so the branch you want live must be pushed.

```powershell
git push origin main
```

## 2. Create the project and its datastores

1. Sign in at [railway.app](https://railway.app) with GitHub and create a new project.
2. **+ New → Database → PostgreSQL**.
3. **+ New → Database → Redis**.

Leave both alone — you will reference their URLs rather than copying secrets.

## 3. Deploy the backend

**+ New → GitHub Repo →** pick this repository. Then open the service's
**Settings**:

- **Root Directory:** `backend` (this is what makes Railway use `backend/Dockerfile`)
- **Healthcheck Path:** `/api/v1/health`

Under **Variables**, add:

```
ENV=production
SECRET_KEY=<paste a generated value — see below>
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SEED_DEMO_DATA=true
CORS_ORIGINS=http://localhost:5173
```

The `${{...}}` forms are Railway reference variables: they resolve to the
private-network URLs of the two databases, so traffic never leaves the project
and you never paste a password anywhere.

Generate the secret key locally and paste the output:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`ENV=production` makes the app refuse to boot on the placeholder key, so a
deployment can never sign tokens with a value that is public in this repo.

`SEED_DEMO_DATA=true` creates the demo restaurant, floor plan and four logins
on first boot. The seed is idempotent, so leaving it on is harmless — but drop
it if this ever becomes a real deployment.

Now open **Settings → Networking → Generate Domain**. Note the URL, something
like `https://backend-production-a1b2.up.railway.app`. Check that
`<that URL>/api/v1/health` returns `{"status":"ok"}` and `/docs` renders.

## 4. Deploy the frontend

**+ New → GitHub Repo →** the same repository again. In **Settings**:

- **Root Directory:** `frontend`

Under **Variables**:

```
VITE_API_URL=https://<your-backend-domain>/api/v1
```

This one is consumed at **build** time (Vite inlines it into the bundle), so
changing it later requires a redeploy, not just a restart. The WebSocket URL is
derived from it automatically — `https://` becomes `wss://`.

Then **Generate Domain** for this service too. That URL is what you share.

## 5. Close the CORS loop

Go back to the **backend** service's variables and replace the placeholder with
the frontend's real domain:

```
CORS_ORIGINS=https://<your-frontend-domain>
```

Railway redeploys on save. Multiple origins work as either a comma-separated
list or a JSON array.

## 6. Sign in

The demo accounts all use the password `Password123`:

| Email | Role |
| --- | --- |
| `admin@demo.com` | Administrator |
| `manager@demo.com` | Manager of "Trattoria Demo" — floor plan editor |
| `waiter@demo.com` | Waiter — staff dashboard |
| `customer@demo.com` | Customer — booking flow |

Worth checking, since they exercise the interesting parts: book a table as the
customer and watch it appear on the staff dashboard without a refresh (Redis
pub/sub → WebSocket), and edit the floor plan as the manager.

## Not deployed by default

**Celery worker and beat.** Notification delivery and reminder scheduling run
as separate processes. `NOTIFICATION_SENDER=logged` means nothing is actually
emailed, so a demo does not need them, and skipping them halves the bill. To
add them: two more services, same repo, Root Directory `backend`, same
variables, with **Custom Start Command**:

```
celery -A app.tasks.celery_app worker -l info
celery -A app.tasks.celery_app beat -l info
```

## Notes for later, if this becomes real

- Turn off `SEED_DEMO_DATA` and delete the demo accounts.
- Put the frontend behind a CDN or move it to Vercel/Netlify (both free for
  static hosting) and keep only the API on Railway.
- Back the database up — Railway's included backups are point-in-time on paid
  plans only.
- `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS` are still at
  their generous dev defaults.

## Other hosts

- **Render** — free tier works, with two catches: services sleep after 15
  minutes of inactivity (~30s cold start on the link you share), and free
  Postgres instances are deleted after 90 days.
- **Fly.io** — cheapest at scale and deploys the same Dockerfiles, but you
  manage Postgres and Redis yourself.
- **A VPS** — `infra/docker-compose.yml` already describes the whole stack;
  add a reverse proxy with TLS in front of it.
