"""Unit tests for compensation detection (Phase 7). No camera needed.

Synthetic landmark frames with known slopes/deviations drive each of the three
signatures — one no-fire case and one fire case each.

Run:  python ml/test_compensation.py
  or: pytest ml/test_compensation.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.compensation import CompensationDetector  # noqa: E402


def _blank():
    return [{"id": i, "x_px": 0, "y_px": 0, "x_norm": 0.0, "y_norm": 0.0,
             "visibility": 1.0} for i in range(33)]


def _set(lms, idx, x, y):
    lms[idx]["x_px"] = x
    lms[idx]["y_px"] = y


def _bicep_frame(shoulder_y, elbow_x):
    """Shoulders 80px apart, hip 200px below shoulder (torso_height=200)."""
    lms = _blank()
    _set(lms, 11, 300, shoulder_y)   # L shoulder
    _set(lms, 12, 380, shoulder_y)   # R shoulder (width 80)
    _set(lms, 13, elbow_x, 220)      # L elbow
    _set(lms, 15, elbow_x, 300)      # L wrist
    _set(lms, 23, 300, shoulder_y + 200)  # L hip
    return lms


def _lean_frame(lean_deg, hip=(320, 400), dy=200):
    """Position L shoulder/hip so torso lean from vertical == lean_deg."""
    lms = _blank()
    sh_x = hip[0] + dy * math.tan(math.radians(lean_deg))
    _set(lms, 11, sh_x, hip[1] - dy)
    _set(lms, 23, hip[0], hip[1])
    return lms


def _flare_frame(flare_deg, sh=(320, 200), r=100, dy=200):
    """Position hip/shoulder/elbow so elbow flare angle == flare_deg."""
    lms = _blank()
    _set(lms, 11, sh[0], sh[1])
    _set(lms, 23, sh[0], sh[1] + dy)                       # hip directly below
    _set(lms, 13, sh[0] + r * math.sin(math.radians(flare_deg)),
         sh[1] + r * math.cos(math.radians(flare_deg)))     # elbow at flare angle
    return lms


# ---------------------- Signature 1: shoulder ---------------------- #
def test_shoulder_compensation_does_not_fire_when_stable():
    d = CompensationDetector("bicep_curl")
    d.update_frame(_bicep_frame(100, 290), "UP")           # baseline
    fired = []
    for _ in range(8):  # tiny rise (2px < 8) — below threshold
        fired += d.update_frame(_bicep_frame(98, 291), "DOWN")
    assert fired == []


def test_shoulder_compensation_fires_when_sustained():
    d = CompensationDetector("bicep_curl")
    d.update_frame(_bicep_frame(100, 290), "UP")           # baseline y=100,x=290
    fired = []
    # rise=10 (>8) and drift=6 (>4) for 6 consecutive frames (>=5).
    for _ in range(6):
        fired += d.update_frame(_bicep_frame(90, 296), "DOWN")
    assert len(fired) == 1
    assert fired[0]["code"] == "SHOULDER_COMPENSATION"
    assert fired[0]["severity"] == 3 and fired[0]["muscle"] == "Biceps Brachii"


# ---------------------- Signature 2: glute ------------------------- #
def _run_reps(detector, values, state_exercise_metric):
    """Feed one DOWN frame per rep with the given metric, complete each rep."""
    events = []
    for v in values:
        detector.update_frame(state_exercise_metric(v), "DOWN")
        events += detector.analyse_rep_complete()
    return events


def test_glute_compensation_does_not_fire_when_lean_flat():
    d = CompensationDetector("squat")
    events = _run_reps(d, [30, 30.5, 30, 31, 30.5], _lean_frame)  # ~flat
    assert events == []


def test_glute_compensation_fires_when_lean_trends_up():
    d = CompensationDetector("squat")
    # lean +3 deg/rep (> 2.0 threshold): 30, 33, 36, 39, 42
    events = _run_reps(d, [30, 33, 36, 39, 42], _lean_frame)
    codes = [e["code"] for e in events]
    assert "GLUTE_COMPENSATION" in codes
    ev = next(e for e in events if e["code"] == "GLUTE_COMPENSATION")
    assert ev["muscle"] == "Gluteus Maximus" and ev["severity"] == 3


# ---------------------- Signature 3: pectoral ---------------------- #
def test_pectoral_compensation_does_not_fire_when_flare_flat():
    d = CompensationDetector("pushup")
    events = _run_reps(d, [40, 41, 40, 41, 40], _flare_frame)  # ~flat
    assert events == []


def test_pectoral_compensation_fires_when_flare_trends_up():
    d = CompensationDetector("pushup")
    # flare +4 deg/rep (> 3.0 threshold): 40, 44, 48, 52, 56
    events = _run_reps(d, [40, 44, 48, 52, 56], _flare_frame)
    codes = [e["code"] for e in events]
    assert "PECTORAL_COMPENSATION" in codes
    ev = next(e for e in events if e["code"] == "PECTORAL_COMPENSATION")
    assert ev["muscle"] == "Pectoralis Major"


def test_reset_set_clears_state():
    d = CompensationDetector("squat")
    _run_reps(d, [30, 33, 36], _lean_frame)
    assert len(d.rep_history) == 3
    d.reset_set()
    assert d.rep_history == [] and len(d.frame_buffer) == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all compensation tests passed")
