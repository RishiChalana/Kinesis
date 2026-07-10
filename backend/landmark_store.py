"""TRACK B — Batched landmark writer for the TimescaleDB hypertable (Phase 6).

Writing one row per landmark per frame (33 * 30fps ≈ 1000 rows/s) hammers the
DB. LandmarkBuffer accumulates 33 rows per frame and flushes with a single
bulk_insert_mappings() every FLUSH_EVERY_FRAMES frames, cutting round-trips ~10x.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import LandmarkFrame

FLUSH_EVERY_FRAMES = 10


class LandmarkBuffer:
    def __init__(self, session_id: int, flush_every: int = FLUSH_EVERY_FRAMES):
        self.session_id = session_id
        self.flush_every = flush_every
        self._rows: list[dict] = []
        self._frames_since_flush = 0

    def add_frame(self, frame_id: int, landmarks: list[dict], timestamp=None):
        """Buffer one frame's 33 landmarks. `landmarks` is the canonical list of
        dicts from ml.pose.extract_landmarks. Returns rows written (0 unless a
        flush happened) — but callers should pass a db session to add_frame_db."""
        ts = timestamp or datetime.now(timezone.utc)
        for lm in landmarks:
            self._rows.append({
                "time": ts,
                "session_id": self.session_id,
                "frame_id": frame_id,
                "landmark_id": lm["id"],
                "x_norm": lm["x_norm"],
                "y_norm": lm["y_norm"],
                "visibility": lm["visibility"],
            })
        self._frames_since_flush += 1

    def should_flush(self) -> bool:
        return self._frames_since_flush >= self.flush_every

    def flush(self, db: Session) -> int:
        """Bulk-insert buffered rows and clear the buffer. Returns rows written."""
        if not self._rows:
            self._frames_since_flush = 0
            return 0
        n = len(self._rows)
        db.bulk_insert_mappings(LandmarkFrame, self._rows)
        db.commit()
        self._rows.clear()
        self._frames_since_flush = 0
        return n

    def maybe_flush(self, db: Session) -> int:
        """Flush only when the frame threshold is reached."""
        if self.should_flush():
            return self.flush(db)
        return 0
