"""WebSocket frame-processing wrapper (Phase 9 refactor).

Thin adapter around ml.pipeline.KinesisPipeline: it owns only the concerns the
pipeline shouldn't — base64 JPEG decode, the session registry, and the bounded
thread pool. All actual pose/rep/metric logic lives in KinesisPipeline.

PRIVACY: the decoded pixel frame lives only in memory for one process_frame()
call — flipped, colour-converted, handed to MediaPipe, then discarded. It is
never written to disk, never inserted into any table, never sent back over the
socket. Only derived numeric data leaves here. See docs/privacy_notes.md.
"""

import base64
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from ml.pipeline import ANGLE_TRIPLES, MISSED_FRAMES_LIMIT, KinesisPipeline

# Back-compat alias: pre-refactor code/tests referred to ProcessingSession.
ProcessingSession = KinesisPipeline

__all__ = [
    "FRAME_EXECUTOR", "MISSED_FRAMES_LIMIT", "ANGLE_TRIPLES", "ProcessingSession",
    "KinesisPipeline", "process_frame", "get_processing_session", "close_session",
]

# asyncio.to_thread() would use the loop's DEFAULT executor (bounded at
# min(32, cpu+4), shared with all other run_in_executor work) — too many
# concurrent MediaPipe inferences under load. Use an explicit, small pool.
FRAME_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mp-infer")


def _decode(frame_b64):
    """Decode a data-URL or bare base64 JPEG into a BGR numpy frame."""
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    raw = base64.b64decode(frame_b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


_sessions: dict[str, KinesisPipeline] = {}


def get_processing_session(session_id):
    """Return the live KinesisPipeline for a WS session_id, or None. Lets the
    WS handler (which holds the DB) inspect/persist the signature model."""
    return _sessions.get(session_id)


def process_frame(session_id, frame_b64, exercise="squat", user_id=None):
    """Decode + process one frame for a session. Returns a frame message dict."""
    pipe = _sessions.get(session_id)
    if pipe is None:
        pipe = KinesisPipeline(exercise=exercise, user_id=user_id)
        _sessions[session_id] = pipe
    frame = _decode(frame_b64)
    if frame is None:
        # Undecodable frame counts as a missed frame, same as no-person.
        return pipe.process_landmarks([])
    return pipe.process_frame(frame)


def close_session(session_id):
    pipe = _sessions.pop(session_id, None)
    if pipe is not None:
        pipe.close()
