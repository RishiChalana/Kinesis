# KINESIS backend image (ML + FastAPI).
#
# NOTE: build context must be the REPO ROOT, not ./backend — the backend imports
# the top-level `ml` package. Build with:
#   docker build -f backend/Dockerfile -t kinesis-backend .
#
# Uses python:3.12-slim (not 3.10 as in the plan): our validated stack pulls
# numpy 2.5 / scipy 1.18, which require Python 3.11+. On 3.10 pip would silently
# resolve older, untested versions.
#
# Pinned to linux/amd64 (the Render deploy target) because mediapipe 0.10.14 and
# opencv-python 5.0.0.93 ship prebuilt wheels for linux x86_64 but NOT linux
# aarch64 — an arm64 build hangs trying to compile them from source. On Apple
# Silicon this builds under QEMU emulation (slower, but installs real wheels).
FROM --platform=linux/amd64 python:3.12-slim

# OpenCV needs these shared libraries at runtime on Linux. On modern Debian
# (trixie, used by python:3.12-slim) the old libgl1-mesa-glx was replaced by
# libgl1 (provides libGL.so.1); libglib2.0-0 provides libgthread.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better layer caching.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# App code + migrations (backend depends on the ml package too).
COPY backend/ ./backend/
COPY ml/ ./ml/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

EXPOSE 8000

# Default: just serve the API (so `docker run` alone lets /docs load without a
# database). docker-compose overrides this to run migrations first — see
# backend/docker-entrypoint.sh.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
