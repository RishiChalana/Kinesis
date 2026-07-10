"""Phase 6 Track B test — landmark hypertable insert + /angles query.

RUN ONLY AFTER the migration 9ba3bc559aa4 is applied (alembic upgrade head).

Verifies:
  1. landmark_frames is a real TimescaleDB hypertable.
  2. compression (7d) + retention (90d) policies are registered.
  3. LandmarkBuffer bulk-inserts frames.
  4. GET /sessions/{id}/angles?landmark=LEFT_KNEE returns the time-series.

Cleans up the test user + inserted frames afterward.
Requires the server running:  uvicorn backend.main:app --port 8000
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text  # noqa: E402

from backend.database import SessionLocal  # noqa: E402
from backend.landmark_store import LandmarkBuffer  # noqa: E402
from backend.landmarks import POSE_LANDMARK_IDS  # noqa: E402
from backend.models import LandmarkFrame, User  # noqa: E402

BASE = "http://localhost:8000"
EMAIL = "phase6test@example.com"


def req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or "null")


def cleanup(session_id=None):
    db = SessionLocal()
    if session_id is not None:
        db.execute(
            text("DELETE FROM landmark_frames WHERE session_id = :sid"),
            {"sid": session_id},
        )
    u = db.scalar(select(User).where(User.email == EMAIL))
    if u:
        db.delete(u)
    db.commit()
    db.close()


def check_timescale_objects():
    db = SessionLocal()
    is_hyper = db.execute(text(
        "SELECT count(*) FROM timescaledb_information.hypertables "
        "WHERE hypertable_name = 'landmark_frames'"
    )).scalar()
    policies = db.execute(text(
        "SELECT proc_name FROM timescaledb_information.jobs "
        "WHERE hypertable_name = 'landmark_frames'"
    )).all()
    db.close()
    proc_names = {p[0] for p in policies}
    print(f"is hypertable: {bool(is_hyper)}")
    print(f"registered policy jobs: {sorted(proc_names)}")
    assert is_hyper, "landmark_frames is NOT a hypertable"
    assert "policy_compression" in proc_names, "compression policy missing"
    assert "policy_retention" in proc_names, "retention policy missing"


def main():
    cleanup()

    check_timescale_objects()

    # register + login + start a session
    req("POST", "/auth/register",
        body={"name": "P6", "email": EMAIL, "password": "pw12345"})
    tok = req("POST", "/auth/login",
              body={"email": EMAIL, "password": "pw12345"})[1]["access_token"]
    sid = req("POST", "/sessions/start", token=tok,
              body={"exercise": "squat", "target_sets": 1,
                    "reps_per_set": 1})[1]["session_id"]

    # Insert 25 fake frames of 33 landmarks via the buffer (flushes every 10).
    db = SessionLocal()
    buf = LandmarkBuffer(session_id=sid)
    base_t = datetime.now(timezone.utc)
    total = 0
    for f in range(25):
        landmarks = [
            {"id": i, "x_norm": 0.5, "y_norm": 0.3 + 0.01 * f + 0.001 * i,
             "visibility": 0.9}
            for i in range(33)
        ]
        buf.add_frame(f, landmarks, timestamp=base_t + timedelta(milliseconds=33 * f))
        total += buf.maybe_flush(db)
    total += buf.flush(db)   # final partial flush
    db.close()
    print(f"inserted rows (25 frames x 33): {total}")

    # Query the LEFT_KNEE trajectory via the endpoint.
    code, series = req("GET", f"/sessions/{sid}/angles?landmark=LEFT_KNEE", token=tok)
    print(f"GET /angles?landmark=LEFT_KNEE -> {code}, points: {len(series)}")
    assert code == 200 and len(series) == 25, series
    print("first point:", series[0], "| last point:", series[-1])

    # Numeric id should resolve the same way.
    code2, series2 = req(
        "GET", f"/sessions/{sid}/angles?landmark={POSE_LANDMARK_IDS['LEFT_KNEE']}",
        token=tok)
    assert code2 == 200 and len(series2) == 25

    cleanup(session_id=sid)
    print("\ncleanup done — all Phase 6 Track B checks passed")


if __name__ == "__main__":
    main()
