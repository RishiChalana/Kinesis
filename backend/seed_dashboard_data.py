"""Seed fake session data so the Phase 8 dashboard has something to render.

Creates (or reuses) a demo user, seeds several sessions across exercises with
per-rep form scores, tempo (incl. isometric), asymmetry, and form errors, ends
each session, then verifies the dashboard endpoints return data.

The demo user is LEFT in place so you can log into the frontend with it:
    email: demo@example.com   password: demo12345

Requires: migration 68259d84c269 applied + server running on :8000.
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://localhost:8000"
EMAIL, PASSWORD = "demo@example.com", "demo12345"


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


# exercise -> list of (form_score, ai, ecc, iso, con, [error_codes]) per rep
SESSIONS = [
    ("squat", [(92, 4, 2.8, 0.9, 1.3, []), (88, 6, 2.6, 0.8, 1.4, ["SHALLOW_DEPTH"]),
               (82, 11, 2.2, 0.6, 1.6, ["KNEE_CAVE"]), (74, 14, 1.8, 0.4, 1.9, ["KNEE_CAVE", "TORSO_LEAN"])]),
    ("squat", [(90, 5, 2.9, 1.0, 1.2, []), (86, 7, 2.7, 0.9, 1.3, ["TORSO_LEAN"]),
               (80, 12, 2.3, 0.7, 1.5, ["KNEE_CAVE"])]),
    ("deadlift", [(89, 3, 2.5, 0.5, 1.4, []), (84, 8, 2.3, 0.5, 1.6, ["BAR_PATH_DRIFT"]),
                  (78, 13, 2.0, 0.4, 1.8, ["BAR_PATH_DRIFT", "HIP_SHIFT"])]),
    ("pushup", [(91, 4, 2.4, 0.5, 1.0, []), (83, 9, 2.1, 0.4, 1.2, ["ELBOW_FLARE"]),
                (76, 16, 1.7, 0.3, 1.4, ["ELBOW_FLARE"])]),
]


def main():
    code, _ = req("POST", "/auth/register",
                  body={"name": "Demo", "email": EMAIL, "password": PASSWORD})
    print("register:", code, "(409 = already exists, fine)")
    tok = req("POST", "/auth/login", body={"email": EMAIL, "password": PASSWORD})[1]["access_token"]
    uid = req("GET", "/users/me", token=tok)[1]["id"]

    for exercise, reps in SESSIONS:
        sid = req("POST", "/sessions/start", token=tok,
                  body={"exercise": exercise, "target_sets": 1, "reps_per_set": len(reps)})[1]["session_id"]
        for i, (fs, ai, ecc, iso, con, errs) in enumerate(reps, start=1):
            req("POST", f"/sessions/{sid}/reps", token=tok, body={
                "set_number": 1, "rep_number": i, "form_score": fs,
                "tempo_eccentric_s": ecc, "tempo_isometric_s": iso, "tempo_concentric_s": con,
                "left_angle": 90, "right_angle": 90 + ai, "asymmetry_pct": ai,
                "compensation_detected": ai > 12,
                "errors": [{"code": c, "severity": "MEDIUM", "frame_count": 5, "frames_total": 40} for c in errs],
            })
        end = req("PATCH", f"/sessions/{sid}/end", token=tok)[1]
        print(f"  seeded {exercise} session {sid}: avg_form={end['avg_form_score']:.0f} "
              f"avg_ai={end['avg_asymmetry']:.1f} reps={end['rep_count']}")

    print("\n--- verify dashboard endpoints ---")
    sessions = req("GET", "/sessions?limit=100", token=tok)[1]
    print(f"GET /sessions -> {len(sessions)} sessions")
    tempo = req("GET", f"/users/{uid}/tempo-history", token=tok)[1]
    print(f"GET /tempo-history -> {len(tempo)} points; first: {tempo[0] if tempo else None}")
    errs = req("GET", f"/users/{uid}/common-errors", token=tok)[1]
    print(f"GET /common-errors -> {errs}")
    cor = req("GET", "/correctives/KNEE_CAVE", token=tok)[1]
    print(f"GET /correctives/KNEE_CAVE -> cause: {cor['cause']}")

    print(f"\nLog into the frontend as {EMAIL} / {PASSWORD} and open /dashboard.")


if __name__ == "__main__":
    main()
