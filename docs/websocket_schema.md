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

> **Phase 6 shape change:** the flat `asymmetry_pct` / `tempo_phase` /
> `tempo_seconds` fields were replaced by nested `asymmetry` and `tempo`
> objects. Both are `null` on frames where the value doesn't apply (e.g. no rep
> just completed).

```json
{
  "frame_id": 0,
  "timestamp": 1732200000.123,
  "rep_count": 3,
  "state": "DOWN",
  "form_score": 82.0,
  "active_errors": [
    { "code": "KNEE_CAVE", "message": "Left knee caving inward", "severity": "HIGH" }
  ],
  "landmarks": [
    { "id": 25, "x_norm": 0.48, "y_norm": 0.71, "visibility": 0.95 }
  ],
  "left_angle": 88.5,
  "right_angle": 91.2,
  "asymmetry": { "ai_pct": 3.0, "dominant_side": "right", "risk": "OK" },
  "tempo": {
    "phase": "eccentric",
    "eccentric_s": 2.8,
    "isometric_s": 0.9,
    "concentric_s": 1.4,
    "eccentric_ok": true,
    "concentric_ok": true
  },
  "compensation_events": [
    {
      "code": "GLUTE_COMPENSATION",
      "message": "Gluteal fatigue detected. Torso lean increasing across reps.",
      "muscle": "Gluteus Maximus",
      "severity": 3
    }
  ]
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
| `landmarks` | array | `[{id, x_norm, y_norm, visibility}]` — drives the canvas skeleton | Phase 7 |
| `left_angle` | float \| null | Left-side monitored joint angle (deg) | Phase 4/6 |
| `right_angle` | float \| null | Right-side monitored joint angle (deg) | Phase 4/6 |
| `asymmetry` | object \| null | `{ai_pct, dominant_side, risk}` — bilateral AI for the last rep | Phase 6 |
| `tempo` | object \| null | `{phase, eccentric_s, isometric_s, concentric_s, eccentric_ok, concentric_ok}` | Phase 6 |
| `compensation_events` | array | `[{code, message, muscle, severity}]` — Phase 7 multi-joint signatures | Phase 7 |

`asymmetry.risk` is `"OK"` / `"WARNING"` / `"HIGH"`; `dominant_side` is
`"left"` / `"right"` / `"none"`. `tempo.phase` is the current phase name.

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
