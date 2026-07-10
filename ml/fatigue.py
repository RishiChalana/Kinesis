"""TRACK A — Within-set fatigue detection (Phase 8).

Fatigue shows up as form score declining across the reps of a set. We fit a
line to the per-rep form scores and read the slope (points lost per rep).
"""

import numpy as np

FATIGUE_WARNING_SLOPE = -4.0
FATIGUE_DANGER_SLOPE = -8.0
MIN_REPS = 3


class FatigueDetector:
    def __init__(self):
        self.within_set_scores = []

    def reset_set(self):
        """A new set starts fresh — rest restores some capacity."""
        self.within_set_scores = []

    def add(self, form_score):
        """Record a rep's form score and return a fatigue event, or None."""
        if form_score is None:
            return None
        self.within_set_scores.append(form_score)
        if len(self.within_set_scores) < MIN_REPS:
            return None

        n = len(self.within_set_scores)
        slope = float(np.polyfit(range(1, n + 1), self.within_set_scores, 1)[0])

        if slope < FATIGUE_DANGER_SLOPE:
            code, severity = "FATIGUE_DANGER", "DANGER"
        elif slope < FATIGUE_WARNING_SLOPE:
            code, severity = "FATIGUE_WARNING", "WARNING"
        else:
            return None

        return {
            "type": "FATIGUE",
            "code": code,
            "severity": severity,
            "slope": slope,
            "message": f"Form declining across reps — slope: {slope:.1f} pts/rep.",
        }
