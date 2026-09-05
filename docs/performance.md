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

> **Note:** this section describes the state at the offload commit, when the flush
> ran on the shared `FRAME_EXECUTOR`. It was later moved to a dedicated
> `FLUSH_EXECUTOR` — see §6 for the current behavior and why.

Reproduce (server running): concurrent WS load harness, 8 sessions × 90 frames,
comparing HEAD (naive-sync) vs the offloaded variant.

---

## 6. Parallel Cassandra dual-write — executor-pool contention and its fix

The parallel Cassandra writer (dual-write alongside TimescaleDB, sharing
`LandmarkBuffer`'s flush cadence) first ran its flush on the **shared**
`FRAME_EXECUTOR` (4 workers, also serving MediaPipe `process_frame`). A flush
holds its worker for tens of ms; on the shared pool that stole inference slots
and throttled every session's fps. The fix (option 2) moves flushes to a
**dedicated** `FLUSH_EXECUTOR` (2 threads), leaving MediaPipe all 4 workers.

Three configs, **8 concurrent WS sessions × 90 real frames**, 3× each, measured
both before and after the fix:

  * **A** — TimescaleDB only
  * **B** — Cassandra only (TS write skipped, to isolate the store)
  * **C** — Dual-write (both, as shipped)

**Combined per-session fps (median of 3):**

| Config | Pre-fix (shared pool) | Post-fix (dedicated pool) | Δ |
|--------|----------------------:|--------------------------:|:--|
| A — TimescaleDB only | 21.2 | **23.9** | +13% |
| B — Cassandra only   | 15.8 | **17.8** | +13% |
| C — Dual-write       | 14.3 | **12.9** | flat (within noise) |

**Per-store write latency & throughput (per 330-row flush, under load):**

| Config | Store | p50 pre → post | p95 pre → post | throughput pre → post |
|--------|-------|---------------:|---------------:|----------------------:|
| A | TimescaleDB | 19–21 → **18–20 ms** | 31–47 → **26–29 ms** | 13.5–17k → **16–17.5k rows/s** |
| B | Cassandra   | 74–80 → **43–53 ms** | 152–241 → **100–117 ms** | 3.4–3.8k → **5.6–6.9k rows/s** |
| C | TimescaleDB | 28–34 → **23 ms** | 98–341 → **33–81 ms** | 5–9k → **10.7–14k rows/s** |
| C | Cassandra   | 55–71 → **41–45 ms** | 129–341 → **115–244 ms** | 3.7–5k → **4.5–5.9k rows/s** |

**Frame drop: 0.00% in all 18 runs. Dual-write parity: exact (TimescaleDB ==
Cassandra == 2,970 rows/session) both pre- and post-fix.**

**Conclusion:**

1. **The fix works for the pool-contention case.** TS-only and Cassandra-only fps
   both rose ~13%, and — more strikingly — Cassandra write throughput nearly
   doubled (3.5k → 6.5k rows/s) with p50 latency down ~40% (75 → 44 ms).
   Mechanism: on the shared pool, the Cassandra driver's worker thread competed
   with CPU-heavy MediaPipe inference for the same 4 threads, starving the
   async-callback processing; on a dedicated pool it gets CPU promptly. Same
   reason TS p95 tightened. This is the coupling problem and its fix, cleanly
   demonstrated.

2. **Dual-write live fps did *not* improve (~13–14 either way).** This is the
   honest, interesting part: in dual mode the flush is ~65–90 ms (TS + Cassandra
   sequential) and it is **awaited in each session's request→response critical
   path** on every 10th frame. That latency serializes into the session's own
   throughput regardless of which pool runs it, so freeing MediaPipe doesn't move
   it. It's a **latency-in-critical-path** problem, not a pool-contention one — a
   different bottleneck that option 2 isn't designed to solve.

3. So option 2 is the right fix for the specific coupling identified (and it
   measurably improved per-store throughput and the single-store live paths), but
   it exposes that dual-write's live-fps ceiling is Cassandra's critical-path
   write latency. The lever for that is fire-and-forget Cassandra writes — see
   Future Work.

Per-store numbers are why Cassandra costs more per flush than TimescaleDB in the
first place: TimescaleDB writes 330 rows in one `bulk_insert_mappings`; Cassandra
issues 330 individual async `LOCAL_ONE` inserts (each landmark is its own
partition, so batching cannot help). That is inherent to the schema/access
pattern, not a tuning miss.

Reproduce (both stores running): the A/B/C driver — instrumented server
(monkeypatched flush per `BENCH_MODE`) + 8-session × 90-frame harness, `/bench/stats`
for per-store flush timing.

---

## Future Work — fire-and-forget Cassandra writes (option 3, not implemented)

Finding 2 above shows dual-write's live-fps ceiling is Cassandra's ~50–70 ms
flush sitting in each session's awaited critical path. Option 3 would remove it:
after the TimescaleDB commit (source of truth), hand the rows to a bounded queue
drained by a dedicated Cassandra writer thread and return immediately, instead of
awaiting the Cassandra write. The flush's critical-path cost would drop back to
TimescaleDB-only (~20 ms).

**Deliberately not implemented**, because the tradeoff is real and unresolved:

* **Backpressure.** Awaiting the write gives natural backpressure — a slow
  Cassandra slows the producer. Fire-and-forget removes it: if Cassandra lags,
  the queue grows and must be bounded, forcing a policy choice (drop telemetry vs
  block anyway vs unbounded memory).
* **Observability.** Awaiting surfaces write failures at flush time (logged
  per session). Fire-and-forget decouples the failure from the request, so
  divergence between the stores becomes silent — it needs separate monitoring
  (queue depth, write error rate, periodic parity checks) to stay trustworthy.

Given Cassandra here is a best-effort *mirror* (TimescaleDB is authoritative),
fire-and-forget is defensible — but only with those two mechanisms in place.
Documented as a decision to make explicitly, not to slip in silently.
