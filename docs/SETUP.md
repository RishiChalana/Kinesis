# KINESIS — Local Setup & Run Guide

How to get both servers running on a fresh clone.

## Prerequisites

- **Python 3.12** (MediaPipe has no wheels for 3.13/3.14 yet — use 3.12)
- **Node.js 18+** and npm
- **PostgreSQL + TimescaleDB** running on `localhost:5432`
  (db: `kinesis`, user: `postgres`, password: `kinesis`) — already provided via Docker

## 1. Python virtual environment (backend + ML)

The venv lives in the project root (`venv/`, git-ignored).

Create it (first time only):

```zsh
python3.12 -m venv venv
```

Activate it (every new terminal, zsh):

```zsh
source venv/bin/activate
```

Your prompt now shows `(venv)`. Deactivate any time with:

```zsh
deactivate
```

Install backend dependencies (first time, or when requirements change):

```zsh
pip install -r backend/requirements.txt
```

## 2. Run the backend (FastAPI)

From the **project root**, with the venv activated:

```zsh
uvicorn backend.main:app --reload
```

- API root: http://localhost:8000/
- Interactive docs (Swagger UI): http://localhost:8000/docs

CORS is configured to allow the frontend origin `http://localhost:5173`.

## 3. Run the frontend (React + Vite)

In a **separate terminal**, from the `frontend/` directory:

```zsh
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173

## Verify everything works

1. Backend: open http://localhost:8000/docs — Swagger UI loads and shows the
   `GET /` endpoint. Hitting `/` returns `{"status": "KINESIS backend running"}`.
2. Frontend: open http://localhost:5173 — page title and heading read **KINESIS**.
