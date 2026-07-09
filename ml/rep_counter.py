"""TRACK A — Rep-counting state machine with hysteresis (Phase 4).

Two thresholds with a dead-band between them prevent sensor noise near a single
boundary from triggering dozens of false counts. A rep increments only on a
completed UP -> DOWN -> UP cycle.
"""

import time

# Per-exercise monitored joint and hysteresis thresholds (degrees).
EXERCISE_THRESHOLDS = {
    "squat": {"joint": "knee", "down": 90, "up": 155},
    "deadlift": {"joint": "hip", "down": 70, "up": 155},
    "bicep_curl": {"joint": "elbow", "down": 35, "up": 155},
    "pushup": {"joint": "elbow", "down": 90, "up": 155},
    "lunge": {"joint": "front_knee", "down": 90, "up": 155},
}

# Minimum frames between state transitions — blocks double-counting.
MIN_FRAMES_BETWEEN_TRANSITIONS = 15


class RepCounter:
    def __init__(self, down_threshold, up_threshold,
                 min_frames=MIN_FRAMES_BETWEEN_TRANSITIONS):
        self.state = "UP"
        self.count = 0
        self.down_threshold = down_threshold
        self.up_threshold = up_threshold
        self.min_frames = min_frames
        self.last_transition_frame = 0

        # Phase-6 tempo data: (frame_num, time.time()) at each transition.
        self.entered_down_at = None
        self.exited_down_at = None

    @classmethod
    def for_exercise(cls, exercise, min_frames=MIN_FRAMES_BETWEEN_TRANSITIONS):
        cfg = EXERCISE_THRESHOLDS[exercise]
        return cls(cfg["down"], cfg["up"], min_frames)

    def update(self, angle, frame_num):
        """Feed one frame's monitored angle. Returns True only on the frame
        that completes a rep (the DOWN -> UP transition)."""
        rep_completed = False
        frames_since = frame_num - self.last_transition_frame

        if self.state == "UP":
            # Descend: only enter DOWN once the angle drops below down_threshold
            # and enough frames have passed since the last transition.
            if angle < self.down_threshold and frames_since >= self.min_frames:
                self.state = "DOWN"
                self.last_transition_frame = frame_num
                self.entered_down_at = (frame_num, time.time())

        elif self.state == "DOWN":
            # Ascend: only return to UP once the angle rises above up_threshold.
            if angle > self.up_threshold and frames_since >= self.min_frames:
                self.state = "UP"
                self.last_transition_frame = frame_num
                self.exited_down_at = (frame_num, time.time())
                self.count += 1
                rep_completed = True

        return rep_completed
