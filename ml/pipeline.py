"""KinesisPipeline — the single ML entry point (Phase 9 refactor).

Everything that turns pose data into feedback lives here: angle math, rep
counting, bilateral asymmetry, tempo, compensation, fatigue, and movement
signature. The backend WS wrapper (backend/frame_processor.py) and the
standalone webcam scripts (ml/pose.py) both drive this one class instead of
re-implementing the per-frame logic.

Two entry methods:
    process_frame(frame_bgr)        — runs MediaPipe, then process_landmarks()
    process_landmarks(landmarks)    — pure logic, unit-testable without a camera
Both return a frame-message dict (docs/websocket_schema.md).
"""

import time

import cv2
import mediapipe as mp

from ml.angles import calculate_angle
from ml.asymmetry import AsymmetryAnalyser
from ml.compensation import CompensationDetector
from ml.fatigue import FatigueDetector
from ml.pose import extract_landmarks
from ml.rep_counter import RepCounter
from ml.signature import RepTrajectory, SignatureModel
from ml.tempo import TempoAnalyser

mp_pose = mp.solutions.pose

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


class KinesisPipeline:
    def __init__(self, exercise="squat", user_id=None, user_profile=None,
                 with_pose=True):
        self.exercise = exercise if exercise in ANGLE_TRIPLES else "squat"

        # MediaPipe is optional so process_landmarks() can be unit-tested
        # without loading a model.
        self.pose = None
        if with_pose:
            self.pose = mp_pose.Pose(
                model_complexity=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
            )

        # Phase-5 calibration: personalise the rep thresholds if a profile is
        # supplied, else fall back to population defaults.
        if user_profile is not None:
            t = user_profile.get_exercise_thresholds(self.exercise)
            self.counter = RepCounter(t.get("down"), t.get("up"))
        else:
            self.counter = RepCounter.for_exercise(self.exercise)

        self.asymmetry = AsymmetryAnalyser(self.exercise)
        self.tempo = TempoAnalyser()
        self.compensation = CompensationDetector(self.exercise)
        self.fatigue = FatigueDetector()
        self.signature = SignatureModel(user_id=user_id, exercise=self.exercise)

        self.frame_id = 0
        self.prev_state = self.counter.state
        self._bottom_left = None
        self._bottom_right = None
        self._rep_trajectory = None
        self.last_asymmetry = None
        self.last_tempo = None
        self.last_form_score = None
        self.last_fatigue = None
        self.last_signature = None
        self.missed_frames = 0
        # Set True when a fresh baseline is computed and needs persisting; the
        # WS handler reads this, saves to movement_signatures, and clears it.
        self.signature_needs_save = False

    def process_frame(self, frame_bgr, flip=True):
        """Run pose on a decoded BGR frame, then process the landmarks. The
        pixel frame is used only here and discarded on return (see PRIVACY).
        Pass flip=False if the caller already mirrored the frame for display."""
        now = time.perf_counter()
        if flip:
            frame_bgr = cv2.flip(frame_bgr, 1)
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.pose.process(rgb)
        rgb.flags.writeable = True
        landmarks = extract_landmarks(results, w, h)
        return self.process_landmarks(landmarks, now=now)

    def process_landmarks(self, landmarks, now=None):
        """Advance all analysers for one frame's landmarks. Handles a
        missing-person frame gracefully: the RepCounter is not updated (no
        double-count, no reset), and after MISSED_FRAMES_LIMIT consecutive
        misses we report TRACKING_LOST."""
        now = time.perf_counter() if now is None else now
        self.frame_id += 1

        if landmarks:
            self.missed_frames = 0
        else:
            self.missed_frames += 1

        triples = ANGLE_TRIPLES[self.exercise]
        left_angle = _angle(landmarks, triples["left"])
        right_angle = _angle(landmarks, triples["right"])

        compensation_events = self.compensation.update_frame(
            landmarks, self.counter.state, now=now)

        if left_angle is not None:
            completed = self.counter.update(left_angle, self.frame_id)
            if self.prev_state == "UP" and self.counter.state == "DOWN":
                self.tempo.start_rep()
                self._rep_trajectory = RepTrajectory()
                self._bottom_left = None
                self._bottom_right = None
            if self.counter.state == "DOWN":
                self.tempo.observe(left_angle, now)
                if self._rep_trajectory is not None:
                    self._rep_trajectory.add(left_angle, now)
                if self._bottom_left is None or left_angle < self._bottom_left:
                    self._bottom_left = left_angle
                    self._bottom_right = right_angle
            if completed:
                self._on_rep_complete(compensation_events)
            self.prev_state = self.counter.state

        tracking_lost = self.missed_frames > MISSED_FRAMES_LIMIT
        return {
            "frame_id": self.frame_id,
            "timestamp": time.time(),
            "rep_count": self.counter.count,
            "state": "TRACKING_LOST" if tracking_lost else self.counter.state,
            "active_errors": [],
            "landmarks": [
                {"id": lm["id"], "x_norm": lm["x_norm"], "y_norm": lm["y_norm"],
                 "visibility": lm["visibility"]}
                for lm in landmarks
            ],
            "form_score": self.last_form_score,
            "left_angle": left_angle,
            "right_angle": right_angle,
            "asymmetry": self.last_asymmetry,
            "tempo": self.last_tempo,
            "compensation_events": compensation_events,
            "fatigue": self.last_fatigue,
            "signature": self.last_signature,
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
        rep_comp_events = self.compensation.analyse_rep_complete()
        compensation_events.extend(rep_comp_events)

        # Lightweight form score (interim stand-in for a full FormChecker).
        self.last_form_score = self._score_rep(rep_comp_events, compensation_events)
        self.last_fatigue = self.fatigue.add(self.last_form_score)

        traj = self._rep_trajectory.normalise() if self._rep_trajectory else None
        if traj is not None:
            self.signature.add_good_rep(traj, self.last_form_score)
            if self.signature.baseline_mean is None:
                if self.signature.compute_baseline():
                    self.signature_needs_save = True
            self.last_signature = self.signature.compare(traj)
        self._rep_trajectory = None

    def _score_rep(self, rep_comp_events, all_comp_events):
        score = 100.0
        if self.last_asymmetry:
            risk = self.last_asymmetry["risk"]
            score -= 10 if risk == "WARNING" else 25 if risk == "HIGH" else 0
        if self.last_tempo:
            if self.last_tempo.get("eccentric_ok") is False:
                score -= 10
            if self.last_tempo.get("concentric_ok") is False:
                score -= 10
        if all_comp_events:
            score -= 20
        return max(0.0, min(100.0, score))

    def close(self):
        if self.pose is not None:
            self.pose.close()
