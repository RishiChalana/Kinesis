"""TRACK A — MediaPipe pose pipeline (Phase 3).

Extends the Phase 2 webcam loop with MediaPipe Pose: runs inference per frame,
draws the 33-landmark skeleton, and serialises landmarks into the canonical
dict format every later phase consumes.

Run:  python ml/pose.py   (from the project root, with the venv activated)
Quit: press 'q' in the video window.

------------------------------------------------------------------------------
KEY LANDMARK IDs (MediaPipe Pose, 33 total) — memorise these:
    11, 12  -> left / right SHOULDER   (torso width, shoulder alignment, lean)
    13, 14  -> left / right ELBOW      (bicep curl, elbow flare)
    15, 16  -> left / right WRIST      (bar path, push-up wrist position)
    23, 24  -> left / right HIP        (squat depth, torso angle, asymmetry base)
    25, 26  -> left / right KNEE       (squat rep counter, knee cave, asymmetry)
    27, 28  -> left / right ANKLE      (heel rise, plank line)
    29-32   -> FEET (heel/toe)         (toe position, heel rise detection)
------------------------------------------------------------------------------
"""

import os
import sys
import time

# Allow `python ml/pose.py` (script dir on path) to still import the ml package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Visibility below this is unreliable — gate every landmark use on it.
VISIBILITY_THRESHOLD = 0.5


def extract_landmarks(results, frame_w, frame_h):
    """Serialise MediaPipe results into the canonical landmark format.

    Returns a list of 33 dicts, each:
        {id, x_px, y_px, x_norm, y_norm, visibility}

    This clean format is what every downstream function consumes — raw
    MediaPipe landmark objects must never be passed elsewhere. If no person is
    detected (results.pose_landmarks is None), returns an empty list so callers
    can early-return instead of crashing.
    """
    if results.pose_landmarks is None:
        return []

    landmarks = []
    for idx, lm in enumerate(results.pose_landmarks.landmark):
        landmarks.append(
            {
                "id": idx,
                "x_px": int(lm.x * frame_w),
                "y_px": int(lm.y * frame_h),
                "x_norm": lm.x,
                "y_norm": lm.y,
                "visibility": lm.visibility,
            }
        )
    return landmarks


def _draw_skeleton(frame, landmarks, w, h):
    """Draw landmark dots from the pipeline's canonical landmark list (green
    circles). The full connection skeleton is drawn on the frontend canvas."""
    for lm in landmarks:
        if lm["visibility"] <= VISIBILITY_THRESHOLD:
            continue
        cv2.circle(frame, (int(lm["x_norm"] * w), int(lm["y_norm"] * h)),
                   4, (0, 255, 0), -1)


def main():
    # Post-refactor, this standalone script is a thin wrapper around
    # KinesisPipeline — no duplicated angle/rep logic lives here anymore.
    # Lazy import avoids a circular import (ml.pipeline imports ml.pose).
    from ml.pipeline import ANGLE_TRIPLES, KinesisPipeline

    exercise = sys.argv[1] if len(sys.argv) > 1 else "squat"
    if exercise not in ANGLE_TRIPLES:
        print(f"Unknown exercise '{exercise}'. Choose from {sorted(ANGLE_TRIPLES)}.")
        return

    pipe = KinesisPipeline(exercise=exercise)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: could not open webcam (VideoCapture(0)).")
        return

    prev_time = time.time()
    shape_printed = False
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: failed to read frame; stopping.")
                break

            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame, 1)  # mirror for display
            frame_h, frame_w = frame.shape[:2]
            if not shape_printed:
                print(f"frame.shape = {frame.shape}")
                shape_printed = True

            # flip=False: we already mirrored the display frame, so the pipeline
            # must not flip again (landmarks then align with what's on screen).
            result = pipe.process_frame(frame, flip=False)
            _draw_skeleton(frame, result["landmarks"], frame_w, frame_h)

            now = time.time()
            fps = 1.0 / (now - prev_time) if now > prev_time else 0.0
            prev_time = now

            angle = result["left_angle"]
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame,
                        f"{exercise} angle: {angle:.0f}" if angle is not None
                        else f"{exercise} angle: --",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"REPS: {result['rep_count']}  ({result['state']})",
                        (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            cv2.imshow("KINESIS pose", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        pipe.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
