# KINESIS WebSocket Frame Schema

The contract for the live pose stream between the backend and the React
frontend. Agreed by Person A (CV) and Person B (backend) so both sides
serialise/parse identically.

## Endpoint

```
ws://localhost:8000/ws/{session_id}
```

`session_id` is the id returned by `POST /sessions/start`. One live connection
per session; the server tracks it in `ConnectionManager`.

## Outgoing — server → frontend (one message per processed frame)

```json
{
  "frame_id": 0,
  "timestamp": 1732200000.123,
  "rep_count": 0,
  "state": "UP",
  "form_score": null,
  "active_errors": [
    { "code": "KNEE_CAVE", "message": "Left knee caving inward", "severity": "HIGH" }
  ],
  "left_angle": 172.4,
  "right_angle": 170.9,
  "asymmetry_pct": null,
  "tempo_phase": null,
  "tempo_seconds": null
}
```

| Field | Type | Meaning | Wired in |
|-------|------|---------|----------|
| `frame_id` | int | Monotonic frame counter for the session | Phase 4 |
| `timestamp` | float | `time.time()` when the frame was processed | Phase 4 |
| `rep_count` | int | Completed reps so far this session | Phase 4 |
| `state` | string | Rep state machine: `"UP"` or `"DOWN"` | Phase 4 |
| `form_score` | float \| null | 0–100 form score for the current rep | Phase 5 |
| `active_errors` | array | `[{code, message, severity}]`; empty when clean | Phase 5 |
| `left_angle` | float \| null | Left-side monitored joint angle (deg) | Phase 4/6 |
| `right_angle` | float \| null | Right-side monitored joint angle (deg) | Phase 4/6 |
| `asymmetry_pct` | float \| null | Bilateral asymmetry index (%) | Phase 6 |
| `tempo_phase` | string \| null | `"eccentric"` / `"isometric"` / `"concentric"` | Phase 6 |
| `tempo_seconds` | float \| null | Seconds elapsed in the current tempo phase | Phase 6 |

`form_score`, `active_errors`, `asymmetry_pct`, `tempo_phase`, and
`tempo_seconds` are placeholders (null / empty) in Phase 4 and get populated in
Phases 5–6.

## Incoming — frontend → server

- A frame payload (fields the backend needs to process/echo), or
- A heartbeat reply: `{ "type": "pong" }`

## Heartbeat / keepalive

When no message arrives for **10 seconds**, the server sends:

```json
{ "type": "ping" }
```

If the client does not reply with `{ "type": "pong" }` within **5 seconds**, the
server closes the connection and removes it from `ConnectionManager` to prevent
ghost connections from accumulating.
