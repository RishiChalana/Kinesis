"""Unit tests for asymmetry + tempo (Phase 6). No camera needed.

Run:  python ml/test_asymmetry_tempo.py
  or: pytest ml/test_asymmetry_tempo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.asymmetry import AsymmetryAnalyser  # noqa: E402
from ml.tempo import TempoAnalyser  # noqa: E402


# --------------------------- asymmetry --------------------------- #
def test_ai_formula_known_input():
    a = AsymmetryAnalyser("squat")
    # |105-95| / ((105+95)/2) * 100 = 10/100*100 = 10.0
    out = a.analyse_rep(105, 95)
    assert abs(out["ai_percent"] - 10.0) < 1e-9
    assert out["dominant_side"] == "LEFT"


def test_ai_zero_when_symmetric():
    out = AsymmetryAnalyser().analyse_rep(90, 90)
    assert out["ai_percent"] == 0.0
    assert out["dominant_side"] == "NONE"
    assert out["risk_level"] == "OK"


def test_risk_level_boundaries():
    a = AsymmetryAnalyser()
    assert a.analyse_rep(104, 96)["risk_level"] == "OK"        # ai = 8.0  (<10)
    assert a.analyse_rep(105, 95)["risk_level"] == "WARNING"   # ai = 10.0 (>=10)
    assert a.analyse_rep(107.5, 92.5)["risk_level"] == "WARNING"  # ai = 15.0 (<=15)
    assert a.analyse_rep(110, 90)["risk_level"] == "HIGH"      # ai = 20.0 (>15)


def test_bilateral_imbalance_fires_after_three_sets():
    a = AsymmetryAnalyser("squat")
    event = None
    for _ in range(3):                         # 3 sets, left always higher, AI>10
        a.analyse_rep(112, 88)                  # ai ~ 24%, dominant left
        a.analyse_rep(110, 90)                  # ai ~ 20%, dominant left
        event = a.end_set()["event"]
    assert event is not None
    assert event["type"] == "BILATERAL_IMBALANCE"
    assert event["dominant_side"] == "LEFT"
    assert "knee" in event["message"]


def test_no_imbalance_when_sides_alternate():
    a = AsymmetryAnalyser("squat")
    a.analyse_rep(112, 88); a.analyse_rep(112, 88); ev1 = a.end_set()["event"]
    a.analyse_rep(88, 112); a.analyse_rep(88, 112); ev2 = a.end_set()["event"]
    a.analyse_rep(112, 88); a.analyse_rep(112, 88); ev3 = a.end_set()["event"]
    assert ev1 is None and ev2 is None and ev3 is None   # side flips -> no fire


# ----------------------------- tempo ----------------------------- #
def _squat_rep(t):
    """Drive a TempoAnalyser through one fake squat with perf_counter-style
    timestamps t: descend to bottom at 13.0, ascent starts 14.0, rises after."""
    t.start_rep()
    for angle, ts in [
        (150, 10.0), (120, 11.0), (100, 12.0), (85, 13.0),  # descent -> bottom
        (85, 13.5),                                          # hold at bottom
        (90, 14.0), (110, 14.5), (140, 15.0),                # ascent
    ]:
        t.observe(angle, ts)
    return t.finalize(entered_down_at=(0, 10.0), exited_down_at=(0, 15.5))


def test_tempo_durations_from_fake_rep():
    t = TempoAnalyser()
    durations = _squat_rep(t)
    assert abs(durations["eccentric_s"] - 3.0) < 1e-9    # 13.0 - 10.0
    assert abs(durations["isometric_s"] - 1.0) < 1e-9    # 14.0 - 13.0
    assert abs(durations["concentric_s"] - 1.5) < 1e-9   # 15.5 - 14.0


def test_tempo_scoring_squat_all_ok():
    t = TempoAnalyser()
    _squat_rep(t)
    scores = {s["phase"]: s for s in t.score_tempo("squat")}
    assert scores["eccentric"]["ok"] is True     # 3.0 in (2,4)
    assert scores["isometric"]["ok"] is True     # 1.0 in (0.5,1.5)
    assert scores["concentric"]["ok"] is True    # 1.5 in (1,2)


def test_tempo_scoring_flags_too_fast_eccentric():
    t = TempoAnalyser()
    t.start_rep()
    # Bottom reached only 0.5s after entering DOWN -> ballistic eccentric.
    for angle, ts in [(150, 10.0), (85, 10.5), (85, 10.7), (120, 11.2)]:
        t.observe(angle, ts)
    t.finalize(entered_down_at=(0, 10.0), exited_down_at=(0, 12.0))
    ecc = next(s for s in t.score_tempo("squat") if s["phase"] == "eccentric")
    assert ecc["measured"] < 2.0 and ecc["ok"] is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all asymmetry/tempo tests passed")
