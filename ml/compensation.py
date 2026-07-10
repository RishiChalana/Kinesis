"""TRACK A — Compensatory movement detection (Phase 7).

The core innovation: instead of checking joints in isolation, this detects
correlated MULTI-JOINT signatures that only appear as a combined pattern when a
primary muscle fatigues and the body recruits secondary muscles.

Three signatures:
  1. Bicep curl shoulder compensation — INTRA-rep: shoulder rises + elbow drifts
     forward together, sustained 5+ consecutive frames.
  2. Squat glute fatigue — INTER-rep: torso lean angle at the bottom trends
     upward across reps (polyfit slope > +2 deg/rep, n >= 4).
  3. Push-up pectoral fatigue — INTER-rep: elbow flare angle trends upward
     across reps (polyfit slope > +3 deg/rep, n >= 4).
"""

import time
from collections import deque

import numpy as np

from ml.angles import calculate_angle

# Landmark IDs (left side used for single-side measures).
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW = 13
L_WRIST = 15
L_HIP = 23

# Signature-1 thresholds (fractions of body-scale) and sustain length.
SHOULDER_RISE_FRAC = 0.04      # of torso height
ELBOW_DRIFT_FRAC = 0.05        # of shoulder width
SUSTAIN_FRAMES = 5

# Inter-rep trend thresholds.
GLUTE_SLOPE_DEG_PER_REP = 2.0
PECTORAL_SLOPE_DEG_PER_REP = 3.0
MIN_REPS_FOR_TREND = 4


def _lm(landmarks, idx):
    """(x_px, y_px) for a visible landmark, else None."""
    if idx >= len(landmarks):
        return None
    p = landmarks[idx]
    if p["visibility"] <= 0.5:
        return None
    return (p["x_px"], p["y_px"])


def _longest_true_run(bools):
    best = run = 0
    for b in bools:
        run = run + 1 if b else 0
        best = max(best, run)
    return best


class CompensationDetector:
    def __init__(self, exercise):
        self.exercise = exercise
        self.rep_history = []                 # per-rep trend measurements
        self.frame_buffer = deque(maxlen=10)  # intra-rep multi-joint frames

        # Signature-1 baselines (neutral shoulder/elbow, captured during UP).
        self.baseline_shoulder_y = None
        self.baseline_elbow_x = None

        # Per-rep accumulator for inter-rep signatures.
        self._current_rep_metric = None
        # Fire-once-per-set guards.
        self._shoulder_fired = False
        self._trend_fired = False

    def reset_set(self):
        """Compensation builds within a set; a new set starts fresh."""
        self.rep_history = []
        self.frame_buffer.clear()
        self.baseline_shoulder_y = None
        self.baseline_elbow_x = None
        self._current_rep_metric = None
        self._shoulder_fired = False
        self._trend_fired = False

    # ------------------------------------------------------------------ #
    def update_frame(self, landmarks, state, now=None):
        """Called every frame. Returns a list of fired compensation events
        (usually empty)."""
        now = time.time() if now is None else now
        if not landmarks:
            return []
        if self.exercise == "bicep_curl":
            return self._update_bicep(landmarks, state, now)
        if self.exercise == "squat":
            self._track_max_metric(self._torso_lean(landmarks), state)
        elif self.exercise == "pushup":
            self._track_max_metric(self._elbow_flare(landmarks), state)
        return []

    def analyse_rep_complete(self):
        """Called at each rep end. Appends the rep's trend metric and checks the
        inter-rep signatures. Returns a list of fired events."""
        events = []
        if self._current_rep_metric is not None:
            self.rep_history.append(self._current_rep_metric)
        self._current_rep_metric = None

        if len(self.rep_history) >= MIN_REPS_FOR_TREND and not self._trend_fired:
            n = len(self.rep_history)
            slope = float(np.polyfit(range(1, n + 1), self.rep_history, 1)[0])
            if self.exercise == "squat" and slope > GLUTE_SLOPE_DEG_PER_REP:
                self._trend_fired = True
                events.append(self._event(
                    "GLUTE_COMPENSATION",
                    "Gluteal fatigue detected. Torso lean increasing across "
                    "reps — lower back is compensating.",
                    "Gluteus Maximus", "End set or reduce weight."))
            elif self.exercise == "pushup" and slope > PECTORAL_SLOPE_DEG_PER_REP:
                self._trend_fired = True
                events.append(self._event(
                    "PECTORAL_COMPENSATION",
                    "Push-up shifting from chest-dominant to tricep-dominant. "
                    "Consider ending set.",
                    "Pectoralis Major", "Consider ending set."))
        return events

    # ------------------------------------------------------------------ #
    def _update_bicep(self, landmarks, state, now):
        sh = _lm(landmarks, L_SHOULDER)
        sh_r = _lm(landmarks, R_SHOULDER)
        el = _lm(landmarks, L_ELBOW)
        wr = _lm(landmarks, L_WRIST)
        hip = _lm(landmarks, L_HIP)
        if None in (sh, sh_r, el, hip):
            return []

        torso_height = abs(sh[1] - hip[1])
        shoulder_width = abs(sh[0] - sh_r[0])

        # Capture the neutral baseline while the arm is extended (UP state).
        if state == "UP":
            self.baseline_shoulder_y = sh[1]
            self.baseline_elbow_x = el[0]

        compensating = False
        if (self.baseline_shoulder_y is not None and torso_height > 0
                and shoulder_width > 0):
            shoulder_rise = self.baseline_shoulder_y - sh[1]
            elbow_drift = abs(el[0] - self.baseline_elbow_x)
            compensating = (
                shoulder_rise > SHOULDER_RISE_FRAC * torso_height
                and elbow_drift > ELBOW_DRIFT_FRAC * shoulder_width
            )

        self.frame_buffer.append({
            "shoulder_y": sh[1],
            "elbow_x": el[0],
            "wrist_y": wr[1] if wr else None,
            "frame_time": now,
            "compensating": compensating,
        })

        runs = [f["compensating"] for f in self.frame_buffer]
        if _longest_true_run(runs) >= SUSTAIN_FRAMES and not self._shoulder_fired:
            self._shoulder_fired = True
            return [self._event(
                "SHOULDER_COMPENSATION",
                "Shoulder compensation detected — anterior deltoid assisting "
                "as the biceps fatigue.",
                "Biceps Brachii", "Lower the weight or end the set.")]
        return []

    def _track_max_metric(self, value, state):
        if value is None or state != "DOWN":
            return
        if self._current_rep_metric is None or value > self._current_rep_metric:
            self._current_rep_metric = value

    def _torso_lean(self, landmarks):
        sh = _lm(landmarks, L_SHOULDER)
        hip = _lm(landmarks, L_HIP)
        if sh is None or hip is None:
            return None
        dx = sh[0] - hip[0]
        dy = sh[1] - hip[1]
        return float(np.degrees(np.arctan2(abs(dx), abs(dy))))

    def _elbow_flare(self, landmarks):
        hip = _lm(landmarks, L_HIP)
        sh = _lm(landmarks, L_SHOULDER)
        el = _lm(landmarks, L_ELBOW)
        if None in (hip, sh, el):
            return None
        return calculate_angle(
            {"x": hip[0], "y": hip[1]},
            {"x": sh[0], "y": sh[1]},
            {"x": el[0], "y": el[1]},
        )

    @staticmethod
    def _event(code, message, muscle, recommendation):
        return {
            "type": "COMPENSATION",
            "code": code,
            "severity": 3,
            "message": message,
            "muscle": muscle,
            "recommendation": recommendation,
        }
