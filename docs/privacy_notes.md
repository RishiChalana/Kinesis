# Privacy Notes — Raw Video Frames Are Never Persisted

## The design decision

KINESIS processes webcam video but **never stores it**. Raw pixel frames exist
only transiently in memory; only derived **numeric** data (landmark coordinates,
joint angles, rep counts, tempo/asymmetry metrics) is ever sent onward or
written to a database. This is deliberate: the system's value is in the
biomechanical *numbers*, and biometric video is exactly the kind of sensitive
data we choose not to accumulate.

## Where a frame lives, end to end

1. **Browser** captures a webcam frame, encodes it as a base64 JPEG, and sends
   it over the WebSocket (`{frame, session_id, exercise}`). It is not uploaded
   to any storage bucket.
2. **`backend/frame_processor.py`**:
   - `_decode()` turns the base64 string into an in-memory NumPy BGR array.
   - `ProcessingSession.process()` flips it, converts colour, and passes it to
     MediaPipe Pose. The array is a local variable.
   - When `process()` returns, the array goes out of scope and is garbage
     collected. **There is no `cv2.imwrite`, no file open, no DB insert of pixel
     data anywhere in this path.**
3. **Response**: only the numeric frame message (see `docs/websocket_schema.md`
   — landmarks, angles, rep_count, asymmetry, tempo, compensation) is
   serialised back to the client. The image is not echoed back.

You can verify this quickly:

```zsh
grep -nE "imwrite|open\(|\.save\(|to_sql|bulk_insert|INSERT" backend/frame_processor.py
```

The only I/O in that file is reading the incoming base64 string and returning a
JSON-serialisable dict of numbers.

## What *is* persisted, and its lifetime

| Data | Persisted? | Retention |
|------|-----------|-----------|
| Raw video frames / JPEG bytes / pixel arrays | **No** — never written anywhere | discarded in-memory after each frame |
| Landmark coordinates (`landmark_frames`) | Numeric only (x_norm, y_norm, visibility) | compressed after 7 days, deleted after 90 (see `docs/timescale_policy.md`) |
| Rep-level metrics (`reps`, `form_errors`, `workouts`) | Numeric only | kept (small, aggregated) |

Even the persisted landmark coordinates — the closest thing to "body data" we
keep — are covered by the Phase 6 TimescaleDB **retention policy** and auto-
deleted after 90 days. Nothing video-shaped is ever stored, so there is no
recording to leak, subpoena, or exfiltrate.

## Consequence

A user's session can be fully analysed and charted from numeric landmark
trajectories alone. If those numbers are later deleted (retention policy or on
request), no reconstructable image of the person remains, because none was ever
written in the first place.
