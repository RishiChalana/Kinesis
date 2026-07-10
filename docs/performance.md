# KINESIS — Performance Measurements

All numbers below are **real, measured** on the development machine (Apple M2,
Python 3.12, PostgreSQL + TimescaleDB via Docker). Reproduce with the commands
in each section. Absolute timings will vary by machine; the ratios are the point.

---

## 1. Database indexes — `EXPLAIN ANALYZE` on the `/sessions/{id}/detail` joins

The detail endpoint's `selectinload` issues three queries. Benchmarked against a
seeded dataset of **308 workouts / 9,026 reps / 18,022 form_errors** using
`EXPLAIN (ANALYZE, FORMAT JSON)`.

Migration `ba47161738da` adds: `ix_workouts_user_id`, `ix_sets_workout_id`,
`ix_reps_set_id`, `ix_form_errors_rep_id`.

| Query | Before (Seq Scan) | After (Index Scan) | Speedup |
|-------|------------------:|-------------------:|--------:|
| `sets WHERE workout_id = ?` | 0.038 ms | 0.010 ms | 3.8× |
| `reps WHERE set_id IN (...)` | 0.397 ms | 0.010 ms | **40×** |
| `form_errors WHERE rep_id IN (...)` | 0.742 ms | 0.038 ms | **19×** |
| **Total** | **1.177 ms** | **0.058 ms** | **≈20×** |

Every query moved from **Seq Scan → Index Scan**. The gain scales with table
size, so it grows as the user history accumulates.

> `landmark_frames.session_id` was intentionally **not** given a new index — it's
> already covered by the Phase 6 composite `ix_landmark_frames_session_landmark
> (session_id, landmark_id, time DESC)`.

Reproduce:
```
python backend/bench_query_indexes.py    # before applying the migration
alembic upgrade head
python backend/bench_query_indexes.py    # after
```

---

## 2. `bulk_insert_mappings()` vs one-row-at-a-time (landmark_frames)

Inserting **1,000 landmark_frames rows** two ways:

| Method | Time | |
|--------|-----:|--|
| Naive (1,000 individual ORM inserts) | 140.1 ms | |
| `bulk_insert_mappings()` (single call) | 43.3 ms | |
| **Speedup** | | **3.2×** |

This is why the live pipeline batches 33 landmarks × 10 frames per flush rather
than writing per landmark.

Reproduce: `python backend/bench_performance.py`

---

## 3. MediaPipe inference throughput

Sustained pose-estimation throughput through `KinesisPipeline.process_frame`
(640×480 frames).

**Single session:** **91.0 frames/sec** (~11.0 ms/frame) — well above the
~15–30 fps the live stream needs.

**Concurrent sessions** (each its own pipeline, run in parallel):

| Concurrent sessions | fps / session | Aggregate fps |
|--------------------:|--------------:|--------------:|
| 1 | 82.8 | 82.8 |
| 2 | 76.7 | 153.4 |
| 4 | 69.1 | 276.3 |
| 8 | 49.8 | 398.3 |

Per-session throughput stays **above real-time (30 fps) through 8 concurrent
sessions** on this hardware; it degrades gracefully as CPU contention rises. The
server caps concurrent inferences at 4 via `FRAME_EXECUTOR` (see Phase 7), so
beyond 4 simultaneous frames queue rather than oversubscribing the CPU. Practical
guidance: scale horizontally (more backend instances) past a handful of
simultaneous users rather than enlarging the pool.

Reproduce: `python backend/bench_performance.py`

---

## 4. WebSocket stability

- **Drop rate:** 1,000 frames sent, **1,000 received, 0 dropped (0.00%)** —
  well under the 1% target. Echo-path throughput measured at ~6,400 frames/sec.
- **Memory / leak:** after **1,000 connect/disconnect cycles**,
  `ConnectionManager.active_connections` returned to **0** and heap growth was
  **0.9 KB** (tracemalloc before/after) — no leak.

Reproduce (server running): `python backend/test_ws_stability.py`
