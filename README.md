# KINESIS

**A biomechanics-aware fitness intelligence platform that personalises exercise-form
thresholds to your individual body proportions, detects compensatory multi-joint
fatigue patterns, and tracks bilateral asymmetry, tempo, and a per-user movement
signature — real-time, from a single webcam.**

<!-- TODO(demo-gif): add a ~10s demo GIF here after the camera session.
     Record with the flow in docs/real_human_test_protocol.md (login → live squat
     session → skeleton overlay + rep counter → compensation alert → dashboard).
     Keep it < 5 MB; embed as: ![KINESIS demo](docs/assets/demo.gif) -->
> **Demo GIF:** _coming after the recorded camera session._

---

## The 5 innovations

- **Personalised biomechanical calibration** — form thresholds are computed from
  your own measured torso/femur proportions, not population averages. A 45-second
  calibration sets your natural squat depth, lean allowance, and hinge angle.
- **Compensatory movement detection** — detects *correlated multi-joint*
  signatures of fatigue (shoulder shrug in curls, rising torso lean in squats,
  elbow flare in push-ups), not isolated single-joint errors.
- **Bilateral asymmetry scoring** — a left-vs-right Asymmetry Index per rep, an
  injury-risk signal flagged above the clinically meaningful 10–15% band and
  escalated when it persists across sets.
- **Exercise tempo analysis** — times the eccentric / isometric / concentric
  phases of each rep and scores them against evidence-based targets.
- **Movement-signature fingerprinting (DTW)** — builds a personal kinematic
  baseline and uses Dynamic Time Warping to flag reps that deviate > 2.5σ from
  *your own* norm mid-session.

---

## Architecture

<!-- TODO(architecture-diagram): build in draw.io, export PNG to docs/assets/architecture.png,
     then embed: ![Architecture](docs/assets/architecture.png) -->

The diagram should show the end-to-end flow:

- **Browser (React + Canvas)** captures webcam frames → sends base64 JPEG over an
  authenticated **WebSocket** (JWT).
- **FastAPI backend** decodes each frame, runs **MediaPipe Pose** on a bounded
  thread pool, and drives the **`KinesisPipeline`** (angles → rep counter →
  asymmetry → tempo → compensation → fatigue → DTW signature).
- Processed frame messages stream back to the Canvas overlay (skeleton, rep
  counter, live alerts).
- **PostgreSQL + TimescaleDB**: relational tables (users, workouts, sets, reps,
  form_errors, user_profiles, movement_signatures) + a **hypertable** for raw
  landmark time-series (compressed after 7 days, retained 90).
- **Cassandra (optional, off by default)**: a parallel landmark-telemetry writer
  that dual-writes the same time-series alongside TimescaleDB (TimescaleDB stays
  the source of truth). Gated behind `CASSANDRA_ENABLED`; see Quick setup and
  `docs/performance.md` §6.
- **Dashboard** reads aggregates for trend / asymmetry / tempo / error charts.

---

## Tech stack

| Area | Technology |
|------|-----------|
| Pose estimation | MediaPipe Pose |
| Angle & vector math | NumPy, SciPy |
| Signature matching | fastdtw |
| Video / webcam | OpenCV, HTML5 Canvas, getUserMedia |
| Backend | FastAPI, Uvicorn |
| Real-time stream | WebSockets |
| Auth | JWT (python-jose), passlib/bcrypt |
| ORM / migrations | SQLAlchemy 2.0, Alembic |
| Time-series storage | PostgreSQL + TimescaleDB (hypertable) |
| Parallel telemetry store (optional) | Cassandra (dual-write, off by default) |
| Frontend | React, Vite, React Router |
| Charts | Recharts |
| Containerisation | Docker, Docker Compose, nginx |
| Deployment | Render (backend), Vercel (frontend) |

---

## Quick setup

**Everything in one command** (Docker + Docker Compose required):

```bash
# 1. Create .env in the repo root (see .env.example):
#    SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
#    DATABASE_URL is overridden by compose to point at the db service.
docker-compose up --build
```

This starts four services: **TimescaleDB**, a single-node **Cassandra** (dev/bench
only — inert unless dual-write is enabled), the **FastAPI backend** (runs
migrations then serves on `:8000`), and the **nginx-served React app** (`:80`).

- App: http://localhost
- API docs: http://localhost:8000/docs

**Optional — parallel Cassandra dual-write.** Off by default. To turn it on, set
`CASSANDRA_ENABLED=true` in `.env` (and `CASSANDRA_CONTACT_POINTS=cassandra` when
running under Docker Compose; the other `CASSANDRA_*` defaults in `.env.example`
work as-is). The backend then mirrors raw landmark time-series into Cassandra
alongside TimescaleDB. It's best-effort: a Cassandra outage is logged and
swallowed, never breaking the primary TimescaleDB write. See `docs/performance.md`
§6 for the schema, consistency levels, retention, and dual-write benchmarks.

**Local dev without Docker:** see `docs/SETUP.md` (Python 3.12 venv + `uvicorn
backend.main:app --reload`, and `cd frontend && npm run dev`).

---

## Research basis

- **Powers, C.M. (2010).** *The influence of abnormal hip mechanics on knee injury:
  a biomechanical perspective.* J Orthop Sports Phys Ther — basis for hip-abductor
  weakness → knee valgus and for limb-proportion-aware squat thresholds.
- **Salvador, S. & Chan, P. (2007).** *FastDTW: Toward accurate dynamic time warping
  in linear time and space.* Intelligent Data Analysis — the DTW method behind
  movement-signature fingerprinting.
- **Mauntel, T.C. et al. (2017).** *The effects of lower extremity muscle activation
  and passive range of motion on single leg squat performance.* J Strength Cond
  Res — corrective basis for knee-valgus interventions.

(Additional thresholds cite Escamilla, R.F. (2001) on squat biomechanics and NSCA
resistance-training / tempo guidance — see `docs/METHODOLOGY.md`.)

---

## Live demo

<!-- TODO(live-url): add the deployed URL after Render + Vercel deploy
     (see docs/DEPLOYMENT.md). -->
> **Live demo:** _deployment steps prepared in `docs/DEPLOYMENT.md`; URL to be
> added after deploy._

---

## Documentation

- `docs/METHODOLOGY.md` — the calibration/compensation/DTW/asymmetry math with citations
- `docs/performance.md` — measured benchmark numbers (indexes, bulk insert, MediaPipe
  throughput, WS stability, and the Cassandra dual-write / executor-pool-contention study)
- `docs/security_audit.md` — auth / CORS / WS-token audit
- `docs/privacy_notes.md` — why raw video frames are never persisted
- `docs/timescale_policy.md` — compression & retention rationale
- `docs/real_human_test_protocol.md` — the in-person camera test checklist
- `docs/DEPLOYMENT.md` — Render + Vercel deployment steps
