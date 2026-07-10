"""Unit tests for the calibration engine (Phase 5).

Run:  python ml/test_calibration.py
  or: pytest ml/test_calibration.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.calibration import (  # noqa: E402
    CalibrationSession,
    PersonalProfile,
    extract_rep_minima,
    load_thresholds,
)


def _landmarks(coords, visibility=1.0):
    """Build a 33-entry canonical landmark list; coords is {id: (x_px, y_px)}."""
    out = []
    for i in range(33):
        x, y = coords.get(i, (0, 0))
        out.append({"id": i, "x_px": x, "y_px": y, "x_norm": 0.0,
                    "y_norm": 0.0, "visibility": visibility})
    return out


def test_extract_rep_minima_finds_three_dips():
    # standing(170) -> dip to 85 -> up -> dip 82 -> up -> dip 88 -> up
    seq = [170, 150, 110, 85, 110, 150, 170, 150, 100, 82, 100, 160,
           170, 120, 90, 88, 120, 165]
    minima = extract_rep_minima(seq, enter_threshold=120, exit_threshold=140)
    assert len(minima) == 3
    assert minima == [85, 82, 88]


def test_standing_ratios_are_real_numbers():
    # Shoulders 80px apart, hips 60px apart. Vertical mids: shoulder=100,
    # hip=300, knee=450 -> torso=200, femur=150, ratio ~= 1.333.
    coords = {11: (280, 100), 12: (360, 100),
              23: (290, 300), 24: (350, 300),
              25: (295, 450), 26: (345, 450)}
    lm = _landmarks(coords)
    s = CalibrationSession(now=0.0)
    for _ in range(10):
        s.update(lm, now=1.0)          # inside the 5s STANDING window
    s.update(lm, now=6.0)              # past 5s -> advance out of STANDING

    prof = s._compute_profile()
    assert abs(prof.shoulder_width_px - 80.0) < 1e-6
    assert abs(prof.hip_width_px - 60.0) < 1e-6
    assert abs(prof.torso_femur_ratio - (200 / 150)) < 1e-6


def test_squat_depth_threshold_is_natural_plus_five():
    s = CalibrationSession(now=0.0)
    # Directly populate the squat buffer with 3 dips (deepest 85/82/88).
    s.squat_knee_angles = [170, 100, 85, 100, 170, 95, 82, 95, 170, 110, 88,
                           110, 170]
    s.squat_frames = [(85, 42.0), (82, 45.0), (88, 40.0)]
    prof = s._compute_profile()
    # median of [85,82,88] = 85 -> threshold 90; not a fixed 90 by coincidence
    # here, but derived. Lean = lean at deepest (82 -> 45.0) + 10 = 55.
    assert abs(prof.squat_depth_threshold - 90.0) < 1e-6
    assert abs(prof.squat_lean_threshold - 55.0) < 1e-6


def test_state_machine_progresses_to_complete():
    s = CalibrationSession(now=0.0)
    empty = _landmarks({}, visibility=0.0)   # nothing visible -> no collection
    assert s.state == "STANDING"
    assert s.update(empty, now=6.0) == "ARMS_UP"      # >5s
    assert s.update(empty, now=10.0) == "SQUATTING"   # >3s
    assert s.update(empty, now=31.0) == "HINGING"     # >20s
    assert s.update(empty, now=47.0) == "COMPLETE"    # >15s
    assert s.profile is not None


def test_fallback_uses_population_defaults():
    thresholds = load_thresholds(None, "squat")   # uncalibrated user
    assert thresholds["down"] == 90 and thresholds["up"] == 155


def test_profile_override_beats_default():
    prof = PersonalProfile(squat_depth_threshold=83.0, squat_lean_threshold=52.0)
    t = prof.get_exercise_thresholds("squat")
    assert t["down"] == 83.0 and t["lean"] == 52.0 and t["up"] == 155


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all calibration tests passed")
