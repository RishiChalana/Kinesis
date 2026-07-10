"""TRACK A — Exercise tempo analysis (Phase 6).

Every rep has three phases whose durations drive muscle stimulus and injury
risk (NSCA, Essentials of Strength Training & Conditioning — time-under-tension):

    eccentric   — muscle lengthening under load (squat: the descent)
                  = UP->DOWN transition  ..  minimum (deepest) angle
    isometric   — the pause at end range   (squat: bottom hold)
                  = minimum angle          ..  start of ascent
    concentric  — muscle shortening        (squat: the ascent)
                  = start of ascent        ..  DOWN->UP transition

The UP->DOWN (entered_down_at) and DOWN->UP (exited_down_at) timestamps come
from the Phase 4 RepCounter. TempoAnalyser observes per-frame angles during the
DOWN state to locate the bottom and the start of ascent.
"""

# Target phase durations in seconds, per exercise (low, high). Single-value
# targets from the plan (e.g. iso 0.5s) are given a +/-50% band. Source: NSCA
# resistance-training tempo guidelines.
TEMPO_TARGETS = {
    "squat": {"eccentric": (2.0, 4.0), "isometric": (0.5, 1.5), "concentric": (1.0, 2.0)},
    "deadlift": {"eccentric": (2.0, 3.0), "isometric": (0.25, 0.75), "concentric": (1.0, 2.0)},
    "bicep_curl": {"eccentric": (2.0, 3.0), "isometric": (0.25, 0.75), "concentric": (0.5, 1.5)},
}


class TempoAnalyser:
    def __init__(self):
        self.eccentric_duration = None
        self.isometric_duration = None
        self.concentric_duration = None
        self._reset_rep()

    def _reset_rep(self):
        self._bottom_at = None
        self._bottom_angle = None
        self._ascent_start_at = None
        self._prev_angle = None

    def start_rep(self):
        """Call at the UP->DOWN transition to begin tracking a new rep."""
        self._reset_rep()

    def observe(self, angle, timestamp):
        """Call each frame while in the DOWN state, with the monitored angle
        and a high-resolution timestamp (time.perf_counter())."""
        if self._bottom_angle is None or angle < self._bottom_angle:
            # New deepest point — (re)start the bottom, cancel any ascent guess.
            self._bottom_angle = angle
            self._bottom_at = timestamp
            self._ascent_start_at = None
        elif (
            self._ascent_start_at is None
            and self._prev_angle is not None
            and angle > self._prev_angle
        ):
            # Angle turned upward after the bottom — ascent begins.
            self._ascent_start_at = timestamp
        self._prev_angle = angle

    def finalize(self, entered_down_at, exited_down_at):
        """Compute the three phase durations. entered_down_at / exited_down_at
        are the (frame_num, time) tuples stored by RepCounter."""
        t_enter = entered_down_at[1]
        t_exit = exited_down_at[1]
        t_bottom = self._bottom_at if self._bottom_at is not None else t_enter
        t_ascent = self._ascent_start_at if self._ascent_start_at is not None else t_bottom

        self.eccentric_duration = t_bottom - t_enter
        self.isometric_duration = t_ascent - t_bottom
        self.concentric_duration = t_exit - t_ascent
        return {
            "eccentric_s": self.eccentric_duration,
            "isometric_s": self.isometric_duration,
            "concentric_s": self.concentric_duration,
        }

    def score_tempo(self, exercise):
        """Compare measured durations to target ranges. Returns a list of
        {phase, measured, target, ok} — one entry per phase."""
        targets = TEMPO_TARGETS.get(exercise, TEMPO_TARGETS["squat"])
        measured = {
            "eccentric": self.eccentric_duration,
            "isometric": self.isometric_duration,
            "concentric": self.concentric_duration,
        }
        results = []
        for phase, (low, high) in targets.items():
            m = measured[phase]
            ok = m is not None and low <= m <= high
            results.append({
                "phase": phase,
                "measured": m,
                "target": (low, high),
                "ok": ok,
            })
        return results
