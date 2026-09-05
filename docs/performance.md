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

---

## 5. Landmark-persistence wiring — synchronous vs offloaded flush

When the live WS path was wired to persist landmarks (`_persist_landmarks` →
`LandmarkBuffer`), the batched flush every 10 frames does DB I/O. Because the WS
handler runs on the single asyncio event loop, an **inline** flush blocks *every*
concurrent session for the duration of the insert. Measured isolated flush cost
(SessionLocal open + 330-row `bulk_insert_mappings` + commit): **9.6 ms median /
18.3 ms p95 / 109 ms max**.

**A note on method, kept deliberately:** the *first* A/B (single run per config)
appeared to show a ~15–18% fps regression from the synchronous flush. That was
**measurement noise** — the wired run happened to include a 109 ms flush outlier
(checkpoint/GC/thermal) that dragged its single-run median. Re-running **3× per
config** to replicate, the regression did **not** hold: baseline and naive-sync
are statistically indistinguishable. Lesson: single-run fps numbers on this
hardware are noise; replicate before characterizing a regression.

Load test: **8 concurrent WS sessions × 90 real frames** (drawn-figure JPEGs so
MediaPipe emits 33 landmarks/frame → genuine inserts every 10 frames). Per-session
fps across 3 runs each:

| Config | Run 1 | Run 2 | Run 3 | Median fps/session | Aggregate (median) | Frame drop |
|--------|------:|------:|------:|-------------------:|-------------------:|:----------:|
| No wiring (baseline)      | 19.5 | 23.6 | 18.9 | **19.5** | ~156 | **0.00%** |
| Naive-sync wiring         | 19.6 | 20.6 | 20.6 | **20.6** | ~165 | **0.00%** |
| Offloaded wiring          | 22.3 | 22.6 | 23.3 | **22.6** | ~181 | **0.00%** |

**0% frame drop in every config and every run.** (Harness caveat: it does
sequential send/recv per client, which self-throttles — a flush stall delays a
response rather than dropping a frame; a flooding client would stress latency
harder.)

**Conclusion:** the offloaded flush
(`await loop.run_in_executor(FRAME_EXECUTOR, _flush_buffer, buf)`) is the
strongest and most consistent — highest median, tightest spread — and it removes
the event-loop-blocking flush as a category rather than relying on it staying
small. Persistence is lossless in all cases (2,970 rows/session = 90 × 33).

Reproduce (server running): concurrent WS load harness, 8 sessions × 90 frames,
comparing HEAD (naive-sync) vs the offloaded variant.
