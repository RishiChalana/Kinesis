# TimescaleDB Compression & Retention — Architectural Decision

## Why landmark data is a time-series problem

Pose landmarks are high-frequency time-series: **33 landmarks × 3 values × ~30
fps**. A single 10-minute session produces on the order of **600,000 rows**.
Stored as ordinary PostgreSQL rows, time-range queries ("give me the left-knee
trajectory for this session", "all knee angles for user X over the last 10
sessions") scan enormous heaps and slow to a crawl.

`landmark_frames` is therefore a **TimescaleDB hypertable** partitioned by
`time`. TimescaleDB transparently splits it into time-based chunks, so range
queries touch only the relevant chunks and use per-chunk indexes — orders of
magnitude faster, with no query rewrite.

## Two tiers of data, two lifetimes

The core decision: **raw landmark frames are disposable; aggregated rep-level
data is permanent.**

| Data | Where | Lifetime | Why |
|------|-------|----------|-----|
| Raw landmark frames (x/y/visibility per landmark per frame) | `landmark_frames` hypertable | **compressed after 7 days, deleted after 90** | Only needed to (re)compute angles, redraw a trajectory chart, or debug a recent session. Volume is huge; long-term value is low. |
| Rep-level results (form_score, tempo, left/right angles, asymmetry_pct, compensation, form_errors) | `reps`, `form_errors` | **forever** | Small, already summarised, and the basis of every trend: progress charts, asymmetry history, injury-risk longitudinal analysis. |
| Session summaries (avg_form_score, avg_asymmetry) | `workouts` | **forever** | One row per workout; drives the dashboard. |

### Compression policy — `add_compression_policy(..., INTERVAL '7 days')`

After 7 days a session is rarely replayed frame-by-frame, but we may still want
its trajectory. TimescaleDB's native columnar compression shrinks old chunks by
roughly **10×** while keeping them queryable. `compress_segmentby =
'session_id, landmark_id'` groups each landmark's series together so per-landmark
reads stay efficient; `compress_orderby = 'time DESC'` keeps recent-first order.

### Retention policy — `add_retention_policy(..., INTERVAL '90 days')`

After 90 days the raw frames are dropped entirely. By then every durable signal
has already been distilled into the permanent rep-level tables, so nothing of
analytical value is lost — we simply stop paying to store millions of raw
coordinate rows. This is standard production time-series hygiene: **keep the
signal, discard the firehose.**

## Net effect

Recent sessions: full-fidelity, fast. Older sessions: compressed but still
chart-able. Ancient raw data: gone, but every rep, error, tempo and asymmetry
number that mattered lives on in small, permanent tables.
