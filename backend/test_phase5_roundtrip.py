"""Phase 5 Track B round-trip test (stdlib urllib — no extra deps).

register -> login -> profile 404/upsert/get -> start session -> post 3 reps
(2 sets, nested form_errors) -> end session -> get detail.

Then, in-process, replays the exact selectinload /detail query against the same
data with a SQLAlchemy event listener counting SELECTs — proving the loading
strategy issues a flat number of queries, not N+1. Cleans up the test user.

Requires the server running:  uvicorn backend.main:app --port 8000
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import event, select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from backend.database import SessionLocal, engine  # noqa: E402
from backend.models import Rep, Set, User, Workout  # noqa: E402

BASE = "http://localhost:8000"
EMAIL = "phase5test@example.com"


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


def cleanup():
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == EMAIL))
    if u:
        db.delete(u)
        db.commit()
    db.close()


def main():
    cleanup()

    req("POST", "/auth/register",
        body={"name": "Phase5", "email": EMAIL, "password": "pw12345"})
    _, login = req("POST", "/auth/login",
                   body={"email": EMAIL, "password": "pw12345"})
    tok = login["access_token"]
    _, me = req("GET", "/users/me", token=tok)
    uid = me["id"]

    code, _ = req("GET", f"/users/{uid}/profile", token=tok)
    print("GET profile before calibration ->", code, "(expect 404)")
    code, prof = req("POST", f"/users/{uid}/profile", token=tok, body={
        "torso_femur_ratio": 1.33, "shoulder_width_px": 80.0,
        "hip_width_px": 60.0, "squat_depth_threshold": 88.0,
        "squat_lean_threshold": 52.0, "natural_hinge_angle": 78.0})
    print("POST profile ->", code, prof)
    code, _ = req("GET", f"/users/{uid}/profile", token=tok)
    print("GET profile after ->", code)

    _, start = req("POST", "/sessions/start", token=tok, body={
        "exercise": "squat", "target_sets": 2, "reps_per_set": 2})
    sid = start["session_id"]
    print("start ->", start)

    reps = [
        {"set_number": 1, "rep_number": 1, "form_score": 90.0,
         "left_angle": 88.0, "right_angle": 91.0, "asymmetry_pct": 3.3,
         "tempo_eccentric_s": 2.1, "tempo_concentric_s": 1.2,
         "compensation_detected": False, "errors": []},
        {"set_number": 1, "rep_number": 2, "form_score": 82.0,
         "left_angle": 85.0, "right_angle": 95.0, "asymmetry_pct": 11.1,
         "compensation_detected": True,
         "errors": [{"code": "KNEE_CAVE", "severity": "HIGH",
                     "frame_count": 12, "frames_total": 40}]},
        {"set_number": 2, "rep_number": 1, "form_score": 76.0,
         "left_angle": 80.0, "right_angle": 92.0, "asymmetry_pct": 13.9,
         "compensation_detected": True,
         "errors": [{"code": "TORSO_LEAN", "severity": "MEDIUM",
                     "frame_count": 8, "frames_total": 40},
                    {"code": "SHALLOW_DEPTH", "severity": "LOW",
                     "frame_count": 5, "frames_total": 40}]},
    ]
    for r in reps:
        code, out = req("POST", f"/sessions/{sid}/reps", token=tok, body=r)
        print("post rep ->", code, out)

    code, end = req("PATCH", f"/sessions/{sid}/end", token=tok)
    print("end summary ->", end)

    code, detail = req("GET", f"/sessions/{sid}/detail", token=tok)
    n_sets = len(detail["sets"])
    n_reps = sum(len(s["reps"]) for s in detail["sets"])
    n_errs = sum(len(r["form_errors"]) for s in detail["sets"] for r in s["reps"])
    print(f"\nGET /detail -> {code}: {n_sets} sets, {n_reps} reps, "
          f"{n_errs} form_errors")

    # --- prove no N+1: replay the exact selectinload query, count SELECTs --- #
    select_count = {"n": 0}

    def _count(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            select_count["n"] += 1

    db = SessionLocal()
    event.listen(engine, "before_cursor_execute", _count)
    workout = db.scalar(
        select(Workout).where(Workout.id == sid).options(
            selectinload(Workout.sets)
            .selectinload(Set.reps)
            .selectinload(Rep.form_errors)
        )
    )
    # Touch the whole tree to force any lazy loads (there should be none).
    _ = [(s.set_number, [(r.rep_number, len(r.form_errors)) for r in s.reps])
         for s in workout.sets]
    event.remove(engine, "before_cursor_execute", _count)
    db.close()

    print(f"SELECTs issued for the full /detail tree: {select_count['n']}")
    print("  1 (workout) + 1 (sets) + 1 (reps) + 1 (form_errors) = 4, flat.")
    print("  N+1 would grow with rep/error counts; selectinload keeps it "
          "constant regardless of how many reps/errors exist.")

    cleanup()
    print("\ncleanup done")


if __name__ == "__main__":
    main()
