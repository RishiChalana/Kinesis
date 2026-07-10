"""Phase 9 — consolidated ML unit tests (pytest). No camera, no DB.

Covers calculate_angle, the visibility gate, RepCounter (incl. edge cases),
AsymmetryAnalyser, and FatigueDetector — the cases named in the Phase 9 spec.

Run:  pytest ml/test_phase9_units.py -v
  or: pytest            (runs the whole ml/ suite via pytest.ini)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from ml.angles import calculate_angle  # noqa: E402
from ml.asymmetry import AsymmetryAnalyser  # noqa: E402
from ml.fatigue import FatigueDetector  # noqa: E402
from ml.pipeline import _angle  # noqa: E402
from ml.rep_counter import RepCounter  # noqa: E402


# ------------------------------ calculate_angle ------------------------------ #
@pytest.mark.parametrize("a,b,c,expected", [
    ({"x": 0, "y": 0}, {"x": 0, "y": 10}, {"x": 10, "y": 10}, 90.0),   # right angle
    ({"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 20, "y": 0}, 180.0),   # straight line
    ({"x": 1, "y": 0}, {"x": 0, "y": 0}, {"x": -1, "y": 1}, 135.0),    # obtuse
])
def test_calculate_angle_values(a, b, c, expected):
    assert abs(calculate_angle(a, b, c) - expected) < 1e-6


def test_calculate_angle_identical_points_does_not_crash():
    # Zero-length vector (a == b) -> guarded, returns 180.0, no ZeroDivision/NaN.
    assert calculate_angle({"x": 5, "y": 5}, {"x": 5, "y": 5}, {"x": 9, "y": 2}) == 180.0


def _lms(triple_ids, visibility):
    lms = [{"id": i, "x_px": 100 + i, "y_px": 100 + i, "x_norm": 0.0,
            "y_norm": 0.0, "visibility": 1.0} for i in range(33)]
    for idx in triple_ids:
        lms[idx]["visibility"] = visibility
    return lms


def test_angle_returns_none_when_landmark_not_visible():
    triple = (23, 25, 27)                    # squat left knee triple
    assert _angle(_lms(triple, visibility=0.0), triple) is None   # gated out
    assert _angle(_lms(triple, visibility=0.9), triple) is not None


# -------------------------------- RepCounter -------------------------------- #
def _feed(rc, angle, n, start_frame):
    for k in range(n):
        rc.update(angle, start_frame + k)
    return start_frame + n


def test_rep_counter_counts_five_squats():
    # Each phase spans >=16 frames so the 15-frame hysteresis gap is satisfied.
    rc = RepCounter.for_exercise("squat")
    f = 0
    for _ in range(5):
        f = _feed(rc, 80, 16, f)     # DOWN (< 90)
        f = _feed(rc, 170, 16, f)    # UP  (> 155) -> completes a rep
    assert rc.count == 5


def test_rep_counter_hovering_at_threshold_does_not_rack_up_reps():
    # Angle oscillating around the down threshold never exceeds the up
    # threshold, so no full UP->DOWN->UP cycle completes.
    rc = RepCounter.for_exercise("squat")
    for f in range(60):
        rc.update(89 if f % 2 == 0 else 91, f)
    assert rc.count == 0


def test_rep_counter_fast_transition_up_is_blocked():
    # Reach DOWN, then bounce back up within <15 frames — the DOWN->UP
    # transition is suppressed by the hysteresis gap, so no rep is counted.
    rc = RepCounter.for_exercise("squat")
    f = _feed(rc, 80, 16, 0)          # -> DOWN at frame 15
    assert rc.state == "DOWN" and rc.count == 0
    _feed(rc, 170, 5, f)              # only 5 frames up (< 15 since transition)
    assert rc.count == 0 and rc.state == "DOWN"


# ---------------------------- AsymmetryAnalyser ----------------------------- #
def test_asymmetry_symmetric_is_zero_ok():
    out = AsymmetryAnalyser().analyse_rep(90, 90)
    assert out["ai_percent"] == 0.0
    assert out["risk_level"] == "OK"
    assert out["dominant_side"] == "NONE"


def test_asymmetry_85_100_is_high_and_right_dominant():
    out = AsymmetryAnalyser().analyse_rep(85, 100)
    # |85-100| / ((85+100)/2) * 100 = 15 / 92.5 * 100 = 16.216...%
    assert abs(out["ai_percent"] - 16.216216) < 1e-4
    assert out["risk_level"] == "HIGH"
    assert out["dominant_side"] == "RIGHT"


# ----------------------------- FatigueDetector ------------------------------ #
def test_fatigue_no_fire_below_three_reps_or_when_flat():
    f = FatigueDetector()
    assert f.add(90) is None and f.add(88) is None          # < 3 reps
    stable = FatigueDetector()
    assert all(stable.add(s) is None for s in [88, 89, 88])  # flat


def test_fatigue_warning_then_danger():
    warn = FatigueDetector()
    ev = None
    for s in [95, 90, 85]:            # slope -5 (< -4, > -8)
        ev = warn.add(s)
    assert ev["code"] == "FATIGUE_WARNING"

    danger = FatigueDetector()
    for s in [95, 85, 75]:            # slope -10 (< -8)
        ev = danger.add(s)
    assert ev["code"] == "FATIGUE_DANGER" and abs(ev["slope"] + 10.0) < 1e-9
