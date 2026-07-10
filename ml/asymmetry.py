"""TRACK A — Bilateral asymmetry scoring (Phase 6).

Asymmetry Index (AI) is a standard sports-biomechanics metric:

    AI = |left - right| / ((left + right) / 2) * 100

Research (e.g. Bishop et al. 2018; Impellizzeri et al. 2007) treats an inter-limb
asymmetry above ~10-15% as clinically meaningful and associated with elevated
injury risk. We compare left vs right of the SAME joint in the SAME frame — the
two sides are stored separately, never averaged.
"""

# Primary joint per exercise (for directional messaging).
PRIMARY_JOINT = {
    "squat": "knee",
    "deadlift": "hip",
    "lunge": "knee",
    "bicep_curl": "elbow",
    "pushup": "elbow",
}

OK, WARNING, HIGH = "OK", "WARNING", "HIGH"

# Number of consecutive same-side high-asymmetry sets that fire an imbalance.
IMBALANCE_SET_STREAK = 3
IMBALANCE_AI_THRESHOLD = 10.0


class AsymmetryAnalyser:
    def __init__(self, exercise="squat"):
        self.exercise = exercise
        self.joint = PRIMARY_JOINT.get(exercise, "joint")
        self.session_history = []        # ai_percent for every rep
        self._current_set = []           # (ai, dominant_side) for the open set
        self._set_averages = []          # (avg_ai, dominant_side) per closed set

    def analyse_rep(self, left_angle, right_angle):
        """Score one rep's left/right primary-joint angles."""
        mean = (left_angle + right_angle) / 2
        ai = abs(left_angle - right_angle) / mean * 100 if mean else 0.0

        if left_angle > right_angle:
            dominant = "LEFT"
        elif right_angle > left_angle:
            dominant = "RIGHT"
        else:
            dominant = "NONE"

        if ai > 15:
            risk = HIGH
        elif ai >= 10:
            risk = WARNING
        else:
            risk = OK

        self.session_history.append(ai)
        self._current_set.append((ai, dominant))
        return {"ai_percent": ai, "dominant_side": dominant, "risk_level": risk}

    def end_set(self):
        """Close the current set: compute its average AI + majority side, then
        check for a sustained cross-set imbalance. Returns a summary dict (with
        an 'event' key that is a BILATERAL_IMBALANCE dict or None)."""
        if not self._current_set:
            return None
        avg_ai = sum(a for a, _ in self._current_set) / len(self._current_set)
        left_n = sum(1 for _, d in self._current_set if d == "LEFT")
        right_n = sum(1 for _, d in self._current_set if d == "RIGHT")
        side = "LEFT" if left_n > right_n else ("RIGHT" if right_n > left_n else "NONE")

        self._set_averages.append((avg_ai, side))
        self._current_set = []
        return {
            "set_avg_ai": avg_ai,
            "dominant_side": side,
            "event": self._check_imbalance_trend(),
        }

    def _check_imbalance_trend(self):
        """Fire BILATERAL_IMBALANCE if the last N sets all show AI > threshold on
        the same (non-neutral) side."""
        if len(self._set_averages) < IMBALANCE_SET_STREAK:
            return None
        recent = self._set_averages[-IMBALANCE_SET_STREAK:]
        sides = {d for _, d in recent}
        if (
            all(ai > IMBALANCE_AI_THRESHOLD for ai, _ in recent)
            and len(sides) == 1
            and "NONE" not in sides
        ):
            side = recent[0][1]
            other = "RIGHT" if side == "LEFT" else "LEFT"
            return {
                "type": "BILATERAL_IMBALANCE",
                "dominant_side": side,
                "sets": IMBALANCE_SET_STREAK,
                "message": (
                    f"{side.capitalize()} {self.joint} angle consistently "
                    f"greater than {other.lower()} across {IMBALANCE_SET_STREAK} "
                    f"sets — possible {other.lower()}-side weakness."
                ),
            }
        return None
