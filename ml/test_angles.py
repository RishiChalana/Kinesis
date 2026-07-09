"""Unit tests for the angle engine and rep counter (Phase 4).

Run:  python ml/test_angles.py     (plain asserts, no pytest needed)
  or: pytest ml/test_angles.py
"""

import os
import sys

# Allow `python ml/test_angles.py` to import the ml package from the root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.angles import calculate_angle  # noqa: E402
from ml.rep_counter import RepCounter  # noqa: E402


def test_right_angle():
    # The canonical case from the plan: (0,0), (0,10), (10,10) -> exactly 90.0.
    a = {"x": 0, "y": 0}
    b = {"x": 0, "y": 10}
    c = {"x": 10, "y": 10}
    assert calculate_angle(a, b, c) == 90.0


def test_straight_line():
    # Vertex between two colinear opposite points -> 180 degrees.
    a = {"x": 0, "y": 0}
    b = {"x": 10, "y": 0}
    c = {"x": 20, "y": 0}
    assert abs(calculate_angle(a, b, c) - 180.0) < 1e-9


def test_zero_magnitude_guard():
    # If a coincides with the vertex, magnitude is 0 -> guarded to 180.0.
    a = {"x": 5, "y": 5}
    b = {"x": 5, "y": 5}
    c = {"x": 10, "y": 10}
    assert calculate_angle(a, b, c) == 180.0


def test_rep_counts_one_full_cycle():
    # UP -> DOWN -> UP with >=15 frames between transitions = exactly 1 rep.
    rc = RepCounter.for_exercise("squat")
    assert rc.update(170, 0) is False          # standing, stays UP
    assert rc.update(80, 20) is False          # deep -> DOWN (frame 20)
    assert rc.update(75, 30) is False           # still down, no transition
    assert rc.update(160, 40) is True          # back up -> rep completed
    assert rc.count == 1
    assert rc.entered_down_at is not None and rc.exited_down_at is not None


def test_noise_does_not_double_count():
    # Rapid oscillation within the min-frame window must not add extra reps.
    rc = RepCounter.for_exercise("squat")
    rc.update(170, 0)
    rc.update(80, 20)      # DOWN at frame 20
    rc.update(160, 25)     # only 5 frames later -> blocked, still DOWN
    assert rc.count == 0
    assert rc.state == "DOWN"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all angle/rep tests passed")
