"""Unit tests for movement signature (DTW) + fatigue detection (Phase 8).
No camera needed — synthetic trajectories and score sequences.

Run:  python ml/test_signature_fatigue.py
  or: pytest ml/test_signature_fatigue.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from ml.fatigue import FatigueDetector  # noqa: E402
from ml.signature import RepTrajectory, SignatureModel, dtw_distance  # noqa: E402


def _squat_curve(bottom=80.0, top=170.0):
    """A clean squat angle trajectory (down then up), 50 points."""
    return np.concatenate([np.linspace(top, bottom, 25),
                           np.linspace(bottom, top, 25)])


# ------------------------------ RepTrajectory ------------------------------ #
def test_trajectory_resamples_to_50():
    rt = RepTrajectory()
    for i, a in enumerate([170, 150, 120, 90, 80, 100, 140, 170]):  # 8 points
        rt.add(a, timestamp=i * 0.1)
    traj = rt.normalise()
    assert traj.shape == (50,)
    assert abs(traj[0] - 170) < 1e-9 and abs(traj[-1] - 170) < 1e-9


# ------------------------------ DTW distance ------------------------------- #
def test_dtw_small_for_similar_large_for_different():
    base = _squat_curve()
    similar = base + 1.0                    # near-identical shape
    different = _squat_curve(bottom=130.0)  # much shallower squat
    d_similar = dtw_distance(similar, base)
    d_different = dtw_distance(different, base)
    assert d_similar < d_different
    assert d_different > 10 * max(d_similar, 1e-6)


def test_signature_fires_only_on_deviation():
    rng = np.random.default_rng(42)
    model = SignatureModel(user_id=1, exercise="squat")
    base = _squat_curve()
    # 8 good baseline reps: same shape + small noise.
    for _ in range(8):
        traj = base + rng.normal(0, 1.0, size=50)
        assert model.add_good_rep(traj, form_score=90) is True
    assert model.compute_baseline() is True

    # A rep just like the baseline -> within norm -> no event.
    normal_rep = base + rng.normal(0, 1.0, size=50)
    assert model.compare(normal_rep) is None

    # A very different rep (shallow squat) -> beyond 2.5 sigma -> fires.
    deviant = _squat_curve(bottom=130.0)
    event = model.compare(deviant)
    assert event is not None and event["code"] == "SIGNATURE_DEVIATION"
    assert event["distance"] > event["threshold"]


def test_good_rep_gate_rejects_low_scores_and_caps_at_10():
    model = SignatureModel(1, "squat")
    assert model.add_good_rep(_squat_curve(), form_score=80) is False  # <= 85
    for _ in range(12):
        model.add_good_rep(_squat_curve(), form_score=95)
    assert len(model.baseline_trajectories) == 10                      # capped


# -------------------------------- Fatigue ---------------------------------- #
def test_fatigue_needs_three_reps():
    f = FatigueDetector()
    assert f.add(90) is None
    assert f.add(80) is None            # only 2 reps so far


def test_fatigue_no_fire_when_stable():
    f = FatigueDetector()
    assert f.add(88) is None and f.add(89) is None and f.add(88) is None


def test_fatigue_warning_and_danger_levels():
    warn = FatigueDetector()
    # slope -5 pts/rep (< -4, > -8) -> WARNING
    ev = None
    for s in [95, 90, 85]:
        ev = warn.add(s)
    assert ev["code"] == "FATIGUE_WARNING"
    assert "-5.0" in ev["message"]

    danger = FatigueDetector()
    ev = None
    for s in [95, 85, 75]:              # slope -10 pts/rep (< -8) -> DANGER
        ev = danger.add(s)
    assert ev["code"] == "FATIGUE_DANGER"
    assert abs(ev["slope"] - (-10.0)) < 1e-9


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all signature/fatigue tests passed")
