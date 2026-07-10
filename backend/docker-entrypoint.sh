#!/bin/sh
# docker-compose entrypoint: wait for the DB, apply migrations, then serve.
set -e

echo "[entrypoint] applying database migrations..."
until alembic upgrade head; do
  echo "[entrypoint] DB not ready yet — retrying in 2s..."
  sleep 2
done

echo "[entrypoint] starting uvicorn..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
