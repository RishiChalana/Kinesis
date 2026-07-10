# KINESIS — Real-Human Test Protocol

A checklist **you run yourself, in front of your camera** — this cannot be
simulated. It validates that the detectors fire correctly on a real body doing
real (and intentionally imperfect) reps.

## Setup

```zsh
# terminal 1 — backend (SECRET_KEY must be in .env)
source venv/bin/activate
uvicorn backend.main:app --reload
# terminal 2 — frontend
cd frontend && npm run dev
```

Open http://localhost:5173, **log in** (top-right — the WS now requires a token),
grant camera permission. Alternatively test the ML directly without the browser:
`python ml/pose.py squat` (shows reps/angle/state live).

Stand so your **full body is in frame**, side-on for squats, facing the camera
for curls. Record the session (screen + webcam) for the demo video.

---

## Test 1 — Squats: rep accuracy + fatigue + form decline

Do **3 sets of 10 squats**, resting between sets. Make the **last set go to
fatigue** (deliberately slow, shaky final reps).

| Check | Expected | Pass? |
|-------|----------|-------|
| Rep counter | Reads **exactly 10** each set (not 9/11) | ☐ |
| Fatigue warning | `FATIGUE_WARNING` fires by **rep 7–8** of the last set | ☐ |
| Form score | Declines in the **last 2 reps** of the fatigued set | ☐ |
| Signature | After a good baseline forms, a sloppy late rep may fire `SIGNATURE_DEVIATION` | ☐ |

Record: the rep count you counted vs. what the app showed, and which rep number
the fatigue warning appeared on.

---

## Test 2 — Bicep curls: shoulder compensation

Do **3 sets of bicep curls**. First two sets: clean form. **Final set:
intentionally shrug/raise the shoulder on each curl** (mimicking deltoid takeover
as the biceps fatigue).

| Check | Expected | Pass? |
|-------|----------|-------|
| Sets 1–2 | **No** `SHOULDER_COMPENSATION` (purple alert) | ☐ |
| Final set | `SHOULDER_COMPENSATION` **fires** on the shrugged reps | ☐ |
| Trigger latency | Note how many **consecutive frames** it took to fire (design target: ≥5 sustained frames) | ☐ |

Record: the frame count / rough seconds from starting the shrug to the alert.
(Run `python ml/pose.py bicep_curl` if you want to watch the raw angle/state.)

---

## Test 3 — Squats with uneven knees: bilateral asymmetry

Do **one set of squats** while intentionally letting **one knee cave inward /
sit deeper than the other** (uneven left/right knee angle).

| Check | Expected | Pass? |
|-------|----------|-------|
| Asymmetry alert | Orange asymmetry `WARNING`/`HIGH` fires (AI% > 10) | ☐ |
| Dominant side | Reported dominant side matches the knee you favoured | ☐ |
| Symmetric reps | Even squats read `OK` (AI% < 10) | ☐ |

Record: the AI% shown and whether the dominant side was correct.

---

## Test 4 — Graceful degradation (quick)

Mid-set, **step out of frame for ~2 seconds**, then step back.

| Check | Expected | Pass? |
|-------|----------|-------|
| Tracking lost | Grey "Tracking lost — step back into frame" alert appears | ☐ |
| No miscount | Rep count is **preserved** (not reset, not double-counted) | ☐ |
| Resume | Counting resumes normally when you return | ☐ |

---

## Test 5 — Frontend error handling (quick)

| Check | Expected | Pass? |
|-------|----------|-------|
| Deny camera | Clear "Enable camera permission" message, **not** a white screen | ☐ |
| Kill backend mid-session | "Connection lost — reconnecting…" banner, auto-reconnect after 2s | ☐ |
| Not logged in → Start | Toast: "Log in before starting a workout" (WS auth) | ☐ |

---

## Dashboard cross-check

After the sessions above (save reps via a real session or the seed script), open
**/dashboard** and confirm the form-trend, asymmetry, tempo, and error-frequency
charts reflect what you just did; click an error bar → corrective modal; open a
session's **per-rep timeline**.
