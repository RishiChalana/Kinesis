"""Phase 9 — end-to-end API + DB consistency + security audit (httpx).

Covers:
  * Full journey: register -> login -> /users/me -> start -> 10 reps -> end -> detail
  * DB consistency: rep count, form_errors count, per-set avg_form_score
  * Security audit: 401 without token, expired JWT rejected, CORS origin scoping,
    WS handshake rejected without a token / accepted with one.

Requires the server running on :8000.
Run:  python backend/test_e2e_integration.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
import websockets  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402

from backend.auth import ALGORITHM, SECRET_KEY  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.models import FormError, Rep, Set, User, Workout  # noqa: E402

BASE = "http://localhost:8000"
EMAIL, PASSWORD = "e2e@example.com", "pw12345"

# 10 reps with known scores + a known number of form errors (3 total).
REPS = [
    {"form_score": 95, "errors": []},
    {"form_score": 92, "errors": []},
    {"form_score": 90, "errors": ["KNEE_CAVE"]},
    {"form_score": 88, "errors": []},
    {"form_score": 86, "errors": ["TORSO_LEAN"]},
    {"form_score": 84, "errors": []},
    {"form_score": 82, "errors": []},
    {"form_score": 80, "errors": ["SHALLOW_DEPTH"]},
    {"form_score": 78, "errors": []},
    {"form_score": 76, "errors": []},
]


def _clean_user():
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == EMAIL))
    if u:
        db.delete(u)
        db.commit()
    db.close()


def run_http():
    _clean_user()
    c = httpx.Client(base_url=BASE, timeout=30)

    # --- security: protected endpoint without a token -> 401 ---
    assert c.get("/users/me").status_code == 401, "missing token should 401"

    # --- security: expired token -> 401 ---
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        SECRET_KEY, algorithm=ALGORITHM)
    r = c.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401, f"expired token should 401, got {r.status_code}"
    print("security: no-token 401 ok; expired-token 401 ok")

    # --- register + login ---
    assert c.post("/auth/register", json={
        "name": "E2E", "email": EMAIL, "password": PASSWORD}).status_code == 201
    tok = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}

    me = c.get("/users/me", headers=auth)
    assert me.status_code == 200 and me.json()["email"] == EMAIL
    uid = me.json()["id"]

    # --- CORS: allowed origin reflected, disallowed origin not ---
    allowed = c.get("/health", headers={"Origin": "http://localhost:5173"})
    denied = c.get("/health", headers={"Origin": "http://evil.example"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert denied.headers.get("access-control-allow-origin") in (None, "http://localhost:5173") \
        and denied.headers.get("access-control-allow-origin") != "*"
    print("security: CORS scoped to http://localhost:5173 (not '*')")

    # --- session lifecycle ---
    start = c.post("/sessions/start", headers=auth, json={
        "exercise": "squat", "target_sets": 2, "reps_per_set": 5})
    assert start.status_code == 201
    sid = start.json()["session_id"]
    assert start.json()["websocket_url"] == f"/ws/{sid}"

    for i, rep in enumerate(REPS, start=1):
        set_number = 1 if i <= 5 else 2
        r = c.post(f"/sessions/{sid}/reps", headers=auth, json={
            "set_number": set_number, "rep_number": i, "form_score": rep["form_score"],
            "tempo_eccentric_s": 2.5, "tempo_isometric_s": 0.7, "tempo_concentric_s": 1.4,
            "left_angle": 90, "right_angle": 92, "asymmetry_pct": 2.2,
            "compensation_detected": False,
            "errors": [{"code": e, "severity": "MEDIUM", "frame_count": 5,
                        "frames_total": 40} for e in rep["errors"]],
        })
        assert r.status_code == 201, f"rep {i} failed: {r.text}"

    end = c.patch(f"/sessions/{sid}/end", headers=auth).json()
    expected_avg = sum(r["form_score"] for r in REPS) / len(REPS)
    assert end["rep_count"] == 10
    assert abs(end["avg_form_score"] - expected_avg) < 1e-6
    print(f"e2e: 10 reps saved; end avg_form_score={end['avg_form_score']:.2f} "
          f"(expected {expected_avg:.2f})")

    detail = c.get(f"/sessions/{sid}/detail", headers=auth).json()
    n_reps = sum(len(s["reps"]) for s in detail["sets"])
    n_errs = sum(len(r["form_errors"]) for s in detail["sets"] for r in s["reps"])
    assert n_reps == 10 and n_errs == 3
    print(f"e2e: detail has {n_reps} reps, {n_errs} form_errors")
    c.close()
    return uid, sid


def check_db_consistency(uid, sid):
    db = SessionLocal()
    # rep count in DB
    db_reps = db.scalar(
        select(func.count(Rep.id)).join(Set, Rep.set_id == Set.id)
        .where(Set.workout_id == sid))
    assert db_reps == 10, f"DB rep count {db_reps} != 10"

    # form_errors count in DB
    db_errs = db.scalar(
        select(func.count(FormError.id)).join(Rep, FormError.rep_id == Rep.id)
        .join(Set, Rep.set_id == Set.id).where(Set.workout_id == sid))
    sent_errs = sum(len(r["errors"]) for r in REPS)
    assert db_errs == sent_errs, f"DB form_errors {db_errs} != sent {sent_errs}"

    # per-set avg_form_score matches manual recompute from reps
    sets = db.scalars(select(Set).where(Set.workout_id == sid).order_by(Set.set_number)).all()
    for s in sets:
        rep_scores = db.scalars(
            select(Rep.form_score).where(Rep.set_id == s.id)).all()
        manual = sum(rep_scores) / len(rep_scores)
        assert abs(s.avg_form_score - manual) < 1e-6, \
            f"set {s.set_number}: stored {s.avg_form_score} != manual {manual}"
    db.close()
    print(f"db-consistency: reps={db_reps}, form_errors={db_errs}, "
          f"per-set avg_form_score matches manual recompute")


async def check_ws_auth():
    # no token -> handshake rejected
    rejected = False
    try:
        async with websockets.connect("ws://localhost:8000/ws/authtest") as ws:
            await ws.send("{}")
            await asyncio.wait_for(ws.recv(), timeout=3)
    except Exception:
        rejected = True
    assert rejected, "WS without token should be rejected"

    # valid token -> accepted
    c = httpx.Client(base_url=BASE, timeout=30)
    tok = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    c.close()
    async with websockets.connect(f"ws://localhost:8000/ws/authtest?token={tok}") as ws:
        await ws.send('{"frame_id": 1, "state": "UP"}')  # no image -> echo path
        resp = await asyncio.wait_for(ws.recv(), timeout=5)
    assert resp, "authenticated WS should respond"
    print("security: WS rejects no-token, accepts valid token")


def main():
    uid, sid = run_http()
    check_db_consistency(uid, sid)
    asyncio.run(check_ws_auth())
    _clean_user()
    print("\nPASS end-to-end + DB consistency + security audit")


if __name__ == "__main__":
    main()
