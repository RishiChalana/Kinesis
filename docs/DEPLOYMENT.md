# KINESIS — Cloud Deployment Guide

**Status: PREPARED, NOT EXECUTED.** These are the exact steps + environment
variables for you to run yourself (they require your own Render / Vercel / DB
accounts and billing decisions). Nothing here has been deployed.

---

## Overview

- **Backend (FastAPI + MediaPipe)** → **Render** Web Service (Docker).
- **Frontend (React/Vite)** → **Vercel** static build.
- **Database (PostgreSQL + TimescaleDB)** → a managed Postgres with the
  TimescaleDB extension (e.g. Timescale Cloud), or Render PostgreSQL.

> ⚠️ **MediaPipe memory:** the backend loads MediaPipe per session. Render's free
> tier (512 MB) will likely OOM — plan for the **Starter ($7/mo)** instance or
> larger. This is the one cost you can't avoid for the live camera pipeline.

---

## 1. Database (do this first — both services need the URL)

You need a Postgres **with the TimescaleDB extension** (the landmark hypertable
migration requires it). Options:

- **Timescale Cloud** (free trial) — extension preinstalled.
- **Render PostgreSQL** — then run `CREATE EXTENSION IF NOT EXISTS timescaledb;`
  (only if the plan supports it; managed RDS-style Postgres may not — verify).

Capture the connection string, form:
```
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<dbname>
```

Migrations run automatically on backend start via `backend/docker-entrypoint.sh`
(`alembic upgrade head`). If you deploy the backend without that entrypoint, run
migrations once manually against the production `DATABASE_URL`.

---

## 2. Backend on Render (Docker)

1. render.com → **New → Web Service** → connect your GitHub repo.
2. **Runtime: Docker.** Set **Dockerfile path** to `backend/Dockerfile` and
   **Docker build context** to the **repo root** (`.`) — the backend image needs
   the top-level `ml/` package, so the context must be the root, not `/backend`.
3. **Start command:** leave as the image default, or override to run migrations
   first:
   ```
   sh backend/docker-entrypoint.sh
   ```
   (If Render's Postgres add-on isn't ready at first boot, the entrypoint retries
   `alembic upgrade head` until the DB is reachable.)
4. **Instance type:** Starter or higher (see the MediaPipe memory note).
5. **Environment variables** (Render dashboard → Environment):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | your production Postgres URL (from step 1) |
   | `SECRET_KEY`   | `python -c "import secrets; print(secrets.token_hex(32))"` — a fresh one, **not** your local key |

6. Deploy. Note the service URL, e.g. `https://kinesis-backend.onrender.com`.
7. Confirm `https://<backend-url>/docs` loads and `/health` returns `{"status":"ok"}`.

> Non-Docker alternative (if you prefer Render's native Python runtime):
> Build command `pip install -r backend/requirements.txt`, start command
> `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, and run
> `alembic upgrade head` once. The Docker path is recommended (matches local).

---

## 3. Frontend on Vercel

1. vercel.com → **New Project** → import the same GitHub repo.
2. **Framework preset: Vite.** **Root Directory: `frontend`.**
3. **Build command:** `npm run build`  **Output directory:** `dist`.
4. **Environment variable:**

   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://<your-render-backend-url>` (no trailing slash) |

   The frontend derives its API base and WebSocket origin from `VITE_API_URL`
   (`http→ws`, `https→wss`). Vite inlines `VITE_*` vars **at build time**, so if
   you change it you must redeploy.
5. Deploy. Note the URL, e.g. `https://kinesis.vercel.app`.

---

## 4. Wire CORS back to the frontend origin (required)

The backend currently allows only `http://localhost:5173`. After the frontend is
live, add your Vercel origin. In `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://kinesis.vercel.app",   # <-- your Vercel URL
    ],
    ...
)
```

Better: read it from an env var so you don't hardcode/redeploy for each URL, e.g.
`allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")`,
then set `CORS_ORIGINS` on Render. Redeploy the backend after changing this.

The WebSocket auth (JWT query param) already works cross-origin; just make sure
`VITE_API_URL` uses `https://` so the browser upgrades to `wss://`.

---

## 5. Post-deploy smoke test

```bash
curl https://<backend-url>/health
# open https://<frontend-url> → log in → the dashboard REST calls should work.
# Live camera works once CORS + wss are correct (browser needs HTTPS for getUserMedia).
```

> Browsers require **HTTPS** for `getUserMedia` (camera). Vercel + Render both
> serve HTTPS by default, so the deployed app can access the camera; `http://`
> localhost is the only non-HTTPS context browsers allow.

---

## Environment variable summary

| Variable | Where | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | Render (backend) | Postgres+TimescaleDB connection |
| `SECRET_KEY` | Render (backend) | JWT signing key (fresh, secret) |
| `VITE_API_URL` | Vercel (frontend) | Backend base URL, baked at build time |
| `CORS_ORIGINS` *(optional)* | Render (backend) | Comma-separated allowed origins |

Never commit real values — `.env` is git-ignored; use the platform dashboards.
