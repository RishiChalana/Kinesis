"""Phase 7 — server-side per-frame pose processing for the live WebSocket.

Decodes a base64 JPEG from the browser, runs MediaPipe Pose, and returns the
full frame message (landmarks + rep count + bilateral asymmetry + tempo +
compensation events) defined in docs/websocket_schema.md. One stateful
ProcessingSession per WebSocket session_id.

CPU-bound work (decode + MediaPipe) is run OFF the event loop on FRAME_EXECUTOR,
a shared bounded thread pool (see the executor comment below).

PRIVACY: the decoded pixel frame lives only in memory for the duration of one
process() call — it is flipped, colour-converted, and handed to MediaPipe, then
discarded when the function returns. It is never written to disk, never inserted
into any table, and never sent back over the socket. Only derived NUMERIC data
(landmark coordinates, angles, counts) leaves this module. See docs/privacy_notes.md.
"""

import base64
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import mediapipe as mp
import numpy as np

from ml.angles import calculate_angle
from ml.asymmetry import AsymmetryAnalyser
from ml.compensation import CompensationDetector
from ml.pose import extract_landmarks
from ml.rep_counter import RepCounter
from ml.tempo import TempoAnalyser

mp_pose = mp.solutions.pose

# asyncio.to_thread() would use the loop's DEFAULT executor, which is bounded at
# min(32, cpu+4) threads and shared with all other run_in_executor work — too
# many concurrent MediaPipe inferences under load. Use an explicit, small pool
# instead and cap it so N simultaneous sessions can't spawn unbounded threads.
FRAME_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mp-infer")

# Consecutive missing-landmark frames before we declare tracking lost.
MISSED_FRAMES_LIMIT = 15

# (point_a, vertex, point_c) landmark ids per side for the primary joint angle.
ANGLE_TRIPLES = {
    "squat": {"left": (23, 25, 27), "right": (24, 26, 28)},
    "deadlift": {"left": (11, 23, 25), "right": (12, 24, 26)},
    "bicep_curl": {"left": (11, 13, 15), "right": (12, 14, 16)},
    "pushup": {"left": (11, 13, 15), "right": (12, 14, 16)},
    "lunge": {"left": (23, 25, 27), "right": (24, 26, 28)},
}


def _angle(landmarks, triple):
    pts = []
    for idx in triple:
        if idx >= len(landmarks):
            return None
        lm = landmarks[idx]
        if lm["visibility"] <= 0.5:
            return None
        pts.append({"x": lm["x_px"], "y": lm["y_px"]})
    return calculate_angle(pts[0], pts[1], pts[2])


def _decode(frame_b64):
    """Decode a data-URL or bare base64 JPEG into a BGR numpy frame."""
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    raw = base64.b64decode(frame_b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


class ProcessingSession:
    def __init__(self, exercise="squat"):
        self.exercise = exercise if exercise in ANGLE_TRIPLES else "squat"
        self.pose = mp_pose.Pose(
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        self.counter = RepCounter.for_exercise(self.exercise)
        self.asymmetry = AsymmetryAnalyser(self.exercise)
        self.tempo = TempoAnalyser()
        self.compensation = CompensationDetector(self.exercise)

        self.frame_id = 0
        self.prev_state = self.counter.state
        self._bottom_left = None
        self._bottom_right = None
        self.last_asymmetry = None
        self.last_tempo = None
        self.missed_frames = 0

    def process(self, frame_bgr):
        """Run pose on a decoded BGR frame, then process the landmarks. The
        pixel frame is used only here and discarded on return (see PRIVACY)."""
        now = time.perf_counter()
        frame_bgr = cv2.flip(frame_bgr, 1)
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.pose.process(rgb)
        rgb.flags.writeable = True
        landmarks = extract_landmarks(results, w, h)
        return self.process_landmarks(landmarks, now=now)

    def process_landmarks(self, landmarks, now=None):
        """Advance all analysers for one frame's landmarks. Split out from
        process() so it can be unit-tested without a real image/MediaPipe, and
        so a missing-person frame (empty landmarks) is handled gracefully:
        the RepCounter is simply not updated (no double-count, no reset), and
        after MISSED_FRAMES_LIMIT consecutive misses we report TRACKING_LOST."""
        now = time.perf_counter() if now is None else now
        self.frame_id += 1

        # Track how long the person has been out of frame.
        if landmarks:
            self.missed_frames = 0
        else:
            self.missed_frames += 1

        triples = ANGLE_TRIPLES[self.exercise]
        left_angle = _angle(landmarks, triples["left"])
        right_angle = _angle(landmarks, triples["right"])

        compensation_events = self.compensation.update_frame(
            landmarks, self.counter.state, now=now)

        # Rep state transitions.
        if left_angle is not None:
            # UP -> DOWN: begin a new rep's tempo tracking.
            if self.counter.state == "UP":
                pass
            completed = self.counter.update(left_angle, self.frame_id)
            if self.prev_state == "UP" and self.counter.state == "DOWN":
                self.tempo.start_rep()
                self._bottom_left = None
                self._bottom_right = None
            if self.counter.state == "DOWN":
                self.tempo.observe(left_angle, now)
                if self._bottom_left is None or left_angle < self._bottom_left:
                    self._bottom_left = left_angle
                    self._bottom_right = right_angle
            if completed:
                self._on_rep_complete(compensation_events)
            self.prev_state = self.counter.state

        # rep_count and the real UP/DOWN state are preserved across the gap;
        # we only override the *reported* state so the UI can show "we lost you"
        # instead of freezing on stale data or guessing.
        tracking_lost = self.missed_frames > MISSED_FRAMES_LIMIT
        return {
            "frame_id": self.frame_id,
            "timestamp": time.time(),
            "rep_count": self.counter.count,
            "state": "TRACKING_LOST" if tracking_lost else self.counter.state,
            "form_score": None,
            "active_errors": [],
            "landmarks": [
                {"id": lm["id"], "x_norm": lm["x_norm"], "y_norm": lm["y_norm"],
                 "visibility": lm["visibility"]}
                for lm in landmarks
            ],
            "left_angle": left_angle,
            "right_angle": right_angle,
            "asymmetry": self.last_asymmetry,
            "tempo": self.last_tempo,
            "compensation_events": compensation_events,
        }

    def _on_rep_complete(self, compensation_events):
        if self._bottom_left is not None and self._bottom_right is not None:
            res = self.asymmetry.analyse_rep(self._bottom_left, self._bottom_right)
            self.last_asymmetry = {
                "ai_pct": res["ai_percent"],
                "dominant_side": res["dominant_side"],
                "risk": res["risk_level"],
            }
        if self.counter.entered_down_at and self.counter.exited_down_at:
            durations = self.tempo.finalize(
                self.counter.entered_down_at, self.counter.exited_down_at)
            scored = {s["phase"]: s["ok"] for s in self.tempo.score_tempo(self.exercise)}
            self.last_tempo = {
                "phase": "concentric",
                "eccentric_s": durations["eccentric_s"],
                "isometric_s": durations["isometric_s"],
                "concentric_s": durations["concentric_s"],
                "eccentric_ok": scored.get("eccentric"),
                "concentric_ok": scored.get("concentric"),
            }
        compensation_events.extend(self.compensation.analyse_rep_complete())

    def close(self):
        self.pose.close()


_sessions: dict[str, ProcessingSession] = {}


def process_frame(session_id, frame_b64, exercise="squat"):
    """Decode + process one frame for a session. Returns a frame message dict."""
    sess = _sessions.get(session_id)
    if sess is None:
        sess = ProcessingSession(exercise)
        _sessions[session_id] = sess
    frame = _decode(frame_b64)
    if frame is None:
        # Undecodable frame counts as a missed frame, same as no-person.
        return sess.process_landmarks([])
    return sess.process(frame)


def close_session(session_id):
    sess = _sessions.pop(session_id, None)
    if sess is not None:
        sess.close()
