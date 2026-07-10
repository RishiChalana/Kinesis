"""TRACK A — Personalised biomechanical calibration engine (Phase 5).

A 45-second guided sequence measures each user's body proportions and natural
movement mechanics, then computes personalised form thresholds instead of using
population averages. A person with long femurs has a physically different
optimal squat angle than someone with short femurs — this engine measures it.

Run end-to-end in front of the camera:
    python ml/calibration.py            (prints the final PersonalProfile)
    python ml/calibration.py <user_id>  (also POSTs it to the backend)
"""

import os
import sys
import time
from dataclasses import asdict, dataclass

# Allow `python ml/calibration.py` to import the ml package from the root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from ml.angles import calculate_angle
from ml.rep_counter import EXERCISE_THRESHOLDS

# --------------------------------------------------------------------------- #
# State machine definition
# --------------------------------------------------------------------------- #
STATES = ["STANDING", "ARMS_UP", "SQUATTING", "HINGING", "COMPLETE"]

STATE_DURATIONS = {
    "STANDING": 5.0,
    "ARMS_UP": 3.0,
    "SQUATTING": 20.0,
    "HINGING": 15.0,
}

INSTRUCTIONS = {
    "STANDING": "Stand still, upright, facing the camera",
    "ARMS_UP": "Raise both arms to shoulder height",
    "SQUATTING": "Perform 3 slow bodyweight squats",
    "HINGING": "Perform 3 slow hip hinges (RDL motion)",
    "COMPLETE": "Calibration complete!",
}

VISIBILITY_THRESHOLD = 0.5

# MediaPipe landmark IDs used here (left side).
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE = 27


@dataclass
class PersonalProfile:
    torso_femur_ratio: float | None = None
    shoulder_width_px: float | None = None
    hip_width_px: float | None = None
    squat_depth_threshold: float | None = None
    squat_lean_threshold: float | None = None
    natural_hinge_angle: float | None = None

    def get_exercise_thresholds(self, exercise: str) -> dict:
        """Personalised angle limits for an exercise, falling back to the
        population defaults for anything not measured."""
        base = dict(EXERCISE_THRESHOLDS.get(exercise, {}))
        if exercise == "squat":
            if self.squat_depth_threshold is not None:
                base["down"] = self.squat_depth_threshold
            if self.squat_lean_threshold is not None:
                base["lean"] = self.squat_lean_threshold
        elif exercise == "deadlift":
            if self.natural_hinge_angle is not None:
                base["down"] = self.natural_hinge_angle
        return base


def extract_rep_minima(angles, enter_threshold, exit_threshold):
    """Hysteresis dip detection: each time the angle dips below enter_threshold
    and later rises back above exit_threshold, record the minimum reached in
    that dip. Returns one minimum per detected rep."""
    minima = []
    in_dip = False
    current_min = None
    for a in angles:
        if not in_dip:
            if a < enter_threshold:
                in_dip = True
                current_min = a
        else:
            current_min = min(current_min, a)
            if a > exit_threshold:
                minima.append(current_min)
                in_dip = False
                current_min = None
    if in_dip and current_min is not None:
        minima.append(current_min)
    return minima


def _pt(landmarks, idx):
    """Return (x_px, y_px) for a landmark if present and visible, else None."""
    if idx >= len(landmarks):
        return None
    lm = landmarks[idx]
    if lm["visibility"] <= VISIBILITY_THRESHOLD:
        return None
    return (lm["x_px"], lm["y_px"])


def _d(pt):
    return {"x": pt[0], "y": pt[1]}


class CalibrationSession:
    def __init__(self, now=None):
        self.state = "STANDING"
        self.state_start = time.time() if now is None else now
        self.profile = None

        # STANDING buffers
        self.shoulder_widths = []
        self.hip_widths = []
        self.torso_pxs = []
        self.femur_pxs = []
        # SQUATTING buffers
        self.squat_knee_angles = []
        self.squat_frames = []  # (knee_angle, torso_lean_deg)
        # HINGING buffers
        self.hinge_hip_angles = []

    # -- public API -------------------------------------------------------- #
    def update(self, landmarks, now=None):
        """Feed one frame's landmarks. Advances state automatically by timer.
        Returns the (possibly new) current state."""
        now = time.time() if now is None else now
        if self.state == "STANDING":
            self._collect_standing(landmarks)
        elif self.state == "SQUATTING":
            self._collect_squatting(landmarks)
        elif self.state == "HINGING":
            self._collect_hinging(landmarks)

        duration = STATE_DURATIONS.get(self.state)
        if duration is not None and (now - self.state_start) >= duration:
            self._advance(now)
        return self.state

    def instruction(self):
        return INSTRUCTIONS[self.state]

    def time_remaining(self, now=None):
        now = time.time() if now is None else now
        duration = STATE_DURATIONS.get(self.state)
        if duration is None:
            return 0.0
        return max(0.0, duration - (now - self.state_start))

    # -- internals --------------------------------------------------------- #
    def _advance(self, now):
        idx = STATES.index(self.state)
        self.state = STATES[idx + 1]
        self.state_start = now
        if self.state == "COMPLETE":
            self.profile = self._compute_profile()

    def _collect_standing(self, landmarks):
        ls, rs = _pt(landmarks, L_SHOULDER), _pt(landmarks, R_SHOULDER)
        lh, rh = _pt(landmarks, L_HIP), _pt(landmarks, R_HIP)
        lk, rk = _pt(landmarks, L_KNEE), _pt(landmarks, R_KNEE)
        if None in (ls, rs, lh, rh, lk, rk):
            return
        self.shoulder_widths.append(float(np.linalg.norm(np.subtract(ls, rs))))
        self.hip_widths.append(float(np.linalg.norm(np.subtract(lh, rh))))
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        knee_mid_y = (lk[1] + rk[1]) / 2
        self.torso_pxs.append(abs(shoulder_mid_y - hip_mid_y))
        self.femur_pxs.append(abs(hip_mid_y - knee_mid_y))

    def _collect_squatting(self, landmarks):
        hip, knee, ankle = (
            _pt(landmarks, L_HIP),
            _pt(landmarks, L_KNEE),
            _pt(landmarks, L_ANKLE),
        )
        if None in (hip, knee, ankle):
            return
        knee_angle = calculate_angle(_d(hip), _d(knee), _d(ankle))
        self.squat_knee_angles.append(knee_angle)

        # Torso lean from vertical, using the shoulder->hip segment.
        shoulder = _pt(landmarks, L_SHOULDER)
        lean = None
        if shoulder is not None:
            dx = shoulder[0] - hip[0]
            dy = shoulder[1] - hip[1]
            lean = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
        self.squat_frames.append((knee_angle, lean))

    def _collect_hinging(self, landmarks):
        shoulder, hip, knee = (
            _pt(landmarks, L_SHOULDER),
            _pt(landmarks, L_HIP),
            _pt(landmarks, L_KNEE),
        )
        if None in (shoulder, hip, knee):
            return
        self.hinge_hip_angles.append(
            calculate_angle(_d(shoulder), _d(hip), _d(knee))
        )

    def _compute_profile(self):
        def med(xs):
            return float(np.median(xs)) if xs else None

        shoulder_width_px = med(self.shoulder_widths)
        hip_width_px = med(self.hip_widths)
        torso_px = med(self.torso_pxs)
        femur_px = med(self.femur_pxs)
        torso_femur_ratio = (
            torso_px / femur_px if torso_px and femur_px else None
        )

        # Natural squat depth = median of per-rep deepest (minimum) knee angles.
        squat_minima = extract_rep_minima(
            self.squat_knee_angles, enter_threshold=120, exit_threshold=140
        )
        natural_depth = med(squat_minima) if squat_minima else (
            min(self.squat_knee_angles) if self.squat_knee_angles else None
        )
        squat_depth_threshold = (
            natural_depth + 5 if natural_depth is not None else None
        )

        # Forward lean allowance = torso lean at the deepest squat frame + 10.
        squat_lean_threshold = None
        deepest = [f for f in self.squat_frames if f[1] is not None]
        if deepest:
            natural_lean = min(deepest, key=lambda f: f[0])[1]
            squat_lean_threshold = natural_lean + 10

        # Natural hinge angle = median of per-rep deepest hip angles.
        hinge_minima = extract_rep_minima(
            self.hinge_hip_angles, enter_threshold=140, exit_threshold=160
        )
        natural_hinge_angle = med(hinge_minima) if hinge_minima else (
            min(self.hinge_hip_angles) if self.hinge_hip_angles else None
        )

        return PersonalProfile(
            torso_femur_ratio=torso_femur_ratio,
            shoulder_width_px=shoulder_width_px,
            hip_width_px=hip_width_px,
            squat_depth_threshold=squat_depth_threshold,
            squat_lean_threshold=squat_lean_threshold,
            natural_hinge_angle=natural_hinge_angle,
        )


def load_thresholds(profile, exercise):
    """Fallback-aware threshold lookup. If no profile exists (uncalibrated
    user), use population-average defaults and note it — never crash/block."""
    if profile is None:
        print(
            f"[calibration] No profile for this user — using population "
            f"defaults for '{exercise}'. Run calibration for personalised "
            f"form feedback."
        )
        return dict(EXERCISE_THRESHOLDS[exercise])
    return profile.get_exercise_thresholds(exercise)


def save_profile_to_backend(user_id, profile, token, base_url="http://localhost:8000"):
    """Best-effort POST of the calibration profile to the backend. Uses stdlib
    urllib so the ML side needs no extra dependency."""
    import json
    import urllib.error
    import urllib.request

    url = f"{base_url}/users/{user_id}/profile"
    body = json.dumps(asdict(profile)).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[calibration] profile saved (HTTP {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        print(f"[calibration] save failed: HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"[calibration] save failed: {e.reason}")
    return False


def main():
    import cv2

    from ml.pose import extract_landmarks, mp_draw, mp_pose

    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    token = os.getenv("KINESIS_TOKEN")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: could not open webcam (VideoCapture(0)).")
        return

    session = CalibrationSession()
    printed_profile = False

    with mp_pose.Pose(
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    ) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (640, 480))
            frame_h, frame_w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = pose.process(rgb)
            rgb.flags.writeable = True

            landmarks = extract_landmarks(results, frame_w, frame_h)
            if results.pose_landmarks is not None:
                mp_draw.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_draw.DrawingSpec((0, 255, 0), 2, 3),
                    mp_draw.DrawingSpec((255, 255, 255), 2),
                )

            state = session.update(landmarks)

            cv2.putText(frame, session.instruction(), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            if state != "COMPLETE":
                cv2.putText(frame, f"{state}  {session.time_remaining():.0f}s",
                            (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (255, 255, 255), 2)

            if state == "COMPLETE" and not printed_profile:
                print("\n=== PersonalProfile ===")
                for k, v in asdict(session.profile).items():
                    print(f"  {k}: {v}")
                if user_id and token:
                    save_profile_to_backend(user_id, session.profile, token)
                elif user_id:
                    print("[calibration] set KINESIS_TOKEN env var to POST the "
                          "profile to the backend.")
                printed_profile = True

            cv2.imshow("KINESIS calibration", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
