"""Phase 7 patch test — graceful degradation on lost tracking.

Drives a ProcessingSession with SYNTHETIC landmark lists (no camera / no
MediaPipe) via the process_landmarks() seam. Completes rep 1, then injects a
gap of 20 missing-landmark frames in the MIDDLE of rep 2, and asserts:
  * no crash
  * rep_count is NOT reset to 0 during the gap (stays at 1)
  * NO double-count (final count is exactly 2, not 1 or 3)
  * state is reported as TRACKING_LOST once the gap exceeds the limit

Run:  python backend/test_phase7_tracking.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.frame_processor import MISSED_FRAMES_LIMIT, ProcessingSession  # noqa: E402


def squat_lms(knee_angle):
    """33 landmarks positioned so both knee angles == knee_angle exactly."""
    lms = [{"id": i, "x_px": 0, "y_px": 0, "x_norm": 0.0, "y_norm": 0.0,
            "visibility": 0.0} for i in range(33)]

    def setp(idx, x, y):
        lms[idx]["x_px"] = x
        lms[idx]["y_px"] = y
        lms[idx]["x_norm"] = x / 640
        lms[idx]["y_norm"] = y / 480
        lms[idx]["visibility"] = 1.0

    a = math.radians(knee_angle)
    ax = 100 * math.sin(a)
    ay = 100 * math.cos(a)
    # left hip/knee/ankle (23/25/27), right hip/knee/ankle (24/26/28)
    setp(23, 300, 200); setp(25, 300, 300); setp(27, 300 - ax, 300 - ay)
    setp(24, 340, 200); setp(26, 340, 300); setp(28, 340 - ax, 300 - ay)
    return lms


STANDING = 170   # UP
DEEP = 80        # DOWN


def feed(sess, angle, n):
    last = None
    for _ in range(n):
        last = sess.process_landmarks(squat_lms(angle))
    return last


def feed_missing(sess, n):
    msgs = []
    for _ in range(n):
        msgs.append(sess.process_landmarks([]))   # empty = no person
    return msgs


def main():
    sess = ProcessingSession("squat")

    # Rep 1: stand -> deep -> stand  (each phase > 15 frames for the hysteresis
    # min-gap between transitions).
    feed(sess, STANDING, 18)
    feed(sess, DEEP, 18)
    feed(sess, STANDING, 18)
    assert sess.counter.count == 1, f"expected 1 rep, got {sess.counter.count}"

    # Rep 2: start descending into the DOWN state...
    feed(sess, DEEP, 18)
    assert sess.counter.state == "DOWN"
    count_before_gap = sess.counter.count
    assert count_before_gap == 1

    # ...person steps out of frame for 20 frames mid-rep.
    gap_msgs = feed_missing(sess, 20)
    # Count must not change or reset during the gap.
    assert all(m["rep_count"] == 1 for m in gap_msgs), "count changed during gap!"
    # Once we exceed the limit, state must be reported as TRACKING_LOST.
    lost = [m for m in gap_msgs if m["state"] == "TRACKING_LOST"]
    assert len(lost) == 20 - MISSED_FRAMES_LIMIT, \
        f"expected {20 - MISSED_FRAMES_LIMIT} TRACKING_LOST frames, got {len(lost)}"

    # Person returns and finishes rep 2.
    feed(sess, DEEP, 5)          # still down, tracking resumes (state back to DOWN)
    resumed = feed(sess, DEEP, 1)
    assert resumed["state"] == "DOWN", f"state after return: {resumed['state']}"
    final = feed(sess, STANDING, 18)   # rise -> completes rep 2

    assert sess.counter.count == 2, f"expected exactly 2 reps, got {sess.counter.count}"
    assert final["state"] == "UP"

    print(f"rep_count before gap: {count_before_gap}")
    print(f"TRACKING_LOST frames during 20-frame gap: {len(lost)} "
          f"(limit={MISSED_FRAMES_LIMIT})")
    print(f"final rep_count: {sess.counter.count} (no double-count, no reset)")
    print("PASS graceful degradation on lost tracking")


if __name__ == "__main__":
    main()
