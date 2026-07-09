"""TRACK A — OpenCV webcam pipeline (Phase 2).

Opens the default webcam, mirrors and standardises each frame, draws an FPS
counter plus test shapes, and quits cleanly on 'q'. This loop is the skeleton
every later ML phase builds on.

Run:  python ml/webcam.py   (from the project root, with the venv activated)
Quit: press 'q' in the video window.
"""

import time

import cv2


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: could not open webcam (VideoCapture(0)).")
        return

    prev_time = time.time()
    shape_printed = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: failed to read frame; stopping.")
            break

        # Mirror horizontally so the user sees themselves as in a mirror,
        # then standardise size so landmark coordinates are consistent later.
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (640, 480))

        # Print the frame shape exactly once — expect (480, 640, 3).
        if not shape_printed:
            print(f"frame.shape = {frame.shape}")
            shape_printed = True

        # FPS from the time elapsed since the previous frame.
        current_time = time.time()
        elapsed = current_time - prev_time
        fps = 1.0 / elapsed if elapsed > 0 else 0.0
        prev_time = current_time

        # White FPS text (BGR = 255,255,255).
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )

        # Test shapes to confirm drawing works: green rectangle, red circle.
        cv2.rectangle(frame, (50, 80), (250, 280), (0, 255, 0), 2)
        cv2.circle(frame, (150, 180), 40, (0, 0, 255), 2)

        cv2.imshow("KINESIS webcam", frame)

        # waitKey returns -1 if no key; mask to a byte and compare to 'q'.
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
