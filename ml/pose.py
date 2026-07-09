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

import time

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


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: could not open webcam (VideoCapture(0)).")
        return

    prev_time = time.time()
    shape_printed = False

    # model_complexity=1 is the balanced option (0 fastest/less accurate,
    # 2 most accurate/slow). Detection/tracking confidences per Phase 3 spec.
    with mp_pose.Pose(
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    ) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: failed to read frame; stopping.")
                break

            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (640, 480))
            frame_h, frame_w = frame.shape[:2]

            if not shape_printed:
                print(f"frame.shape = {frame.shape}")
                shape_printed = True

            # MediaPipe needs RGB, not BGR. Marking the array non-writeable
            # before process() lets MediaPipe pass it by reference (no copy) —
            # a required perf optimisation. Restore writeable afterwards.
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = pose.process(rgb)
            rgb.flags.writeable = True

            # Canonical landmark list — empty if no person detected.
            landmarks = extract_landmarks(results, frame_w, frame_h)

            # Draw the skeleton: green landmark circles, white connection lines.
            if results.pose_landmarks is not None:
                mp_draw.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_draw.DrawingSpec(
                        color=(0, 255, 0), thickness=2, circle_radius=3
                    ),
                    mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2),
                )

            # Example downstream use: only trust landmarks above the gate.
            visible = sum(
                1 for lm in landmarks if lm["visibility"] > VISIBILITY_THRESHOLD
            )

            current_time = time.time()
            elapsed = current_time - prev_time
            fps = 1.0 / elapsed if elapsed > 0 else 0.0
            prev_time = current_time

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}  landmarks visible: {visible}/33",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.imshow("KINESIS pose", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
