"""Phase 9 — performance benchmarks with REAL measured numbers.

  1. bulk_insert_mappings() vs one-row-at-a-time insert for 1000 landmark_frames.
  2. Sustained MediaPipe inference throughput (frames/sec) for a single session,
     and per-session throughput as concurrent sessions scale (1/2/4/8) — shows
     where frame processing starts to lag under the 4-worker pool.

No server needed. Run:  python backend/bench_performance.py
Writes its numbers to stdout; copy them into docs/performance.md.
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.database import SessionLocal  # noqa: E402
from backend.models import LandmarkFrame  # noqa: E402
from ml.pipeline import KinesisPipeline  # noqa: E402

BENCH_SESSION = 999999


def _rows(n):
    base = datetime.now(timezone.utc)
    out = []
    for k in range(n):
        out.append({
            "time": base, "session_id": BENCH_SESSION,
            "frame_id": k // 33, "landmark_id": k % 33,
            "x_norm": 0.5, "y_norm": 0.5, "visibility": 0.9,
        })
    return out


def _cleanup(db):
    db.execute(text("DELETE FROM landmark_frames WHERE session_id = :s"),
               {"s": BENCH_SESSION})
    db.commit()


def bench_insert(n=1000):
    db = SessionLocal()
    _cleanup(db)

    # naive: one ORM object per row, individual INSERTs.
    rows = _rows(n)
    t0 = time.perf_counter()
    for r in rows:
        db.add(LandmarkFrame(**r))
    db.commit()
    naive = time.perf_counter() - t0
    _cleanup(db)

    # bulk: single bulk_insert_mappings call.
    t0 = time.perf_counter()
    db.bulk_insert_mappings(LandmarkFrame, _rows(n))
    db.commit()
    bulk = time.perf_counter() - t0
    _cleanup(db)
    db.close()

    print(f"[insert] {n} landmark_frames rows:")
    print(f"    naive (one-row-at-a-time): {naive * 1000:8.1f} ms")
    print(f"    bulk_insert_mappings:      {bulk * 1000:8.1f} ms")
    print(f"    speedup:                   {naive / bulk:8.1f}x")
    return naive, bulk


def _run_frames(pipe, frames):
    t0 = time.perf_counter()
    for f in frames:
        pipe.process_frame(f, flip=False)
    return len(frames) / (time.perf_counter() - t0)


def bench_mediapipe(single_frames=60):
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Single-session sustained throughput.
    pipe = KinesisPipeline(exercise="squat")
    fps = _run_frames(pipe, [frame] * single_frames)
    pipe.close()
    print(f"[mediapipe] single session: {fps:.1f} frames/sec "
          f"({1000 / fps:.1f} ms/frame)")

    # Concurrent sessions: each runs its own frames on its own pipeline; K run
    # in parallel. Reports the per-session fps at each concurrency level.
    print("[mediapipe] concurrent sessions (per-session fps):")
    for k in [1, 2, 4, 8]:
        pipes = [KinesisPipeline(exercise="squat") for _ in range(k)]
        frames = [frame] * 30
        with ThreadPoolExecutor(max_workers=k) as ex:
            results = list(ex.map(lambda p: _run_frames(p, frames), pipes))
        for p in pipes:
            p.close()
        per = sum(results) / len(results)
        agg = sum(results)
        print(f"    {k} session(s): {per:5.1f} fps/session, {agg:6.1f} fps aggregate")


if __name__ == "__main__":
    bench_insert()
    print()
    bench_mediapipe()
