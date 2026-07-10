# KINESIS — Security Audit (Phase 9)

Each item below is asserted automatically by
`backend/test_e2e_integration.py` (run against a live server). Status reflects
the current code.

## Authentication

| Check | Status | Where |
|-------|--------|-------|
| Protected REST endpoints return **401 without a token** | ✅ verified | `get_current_user` dependency raises 401 |
| **Expired JWT** (`exp` in the past) is rejected with 401 | ✅ verified | `jwt.decode` raises → 401 |
| Tokens are HS256, signed with a server-only `SECRET_KEY` (in `.env`, git-ignored) | ✅ | `backend/auth.py` |
| Passwords stored bcrypt-hashed, never plaintext | ✅ | `hash_password` / `verify_password` |

## WebSocket authentication (the closed gap)

**Before Phase 9:** the WS accepted any connection and trusted a client-supplied
`user_id` field in the frame payload for signature persistence — a spoofing gap.

**After Phase 9:**

| Check | Status |
|-------|--------|
| WS handshake **rejected without a token** (`?token=` query param) | ✅ verified |
| WS handshake **accepted with a valid token** | ✅ verified |
| Expired/invalid token → handshake rejected (`get_user_id_from_token` returns None) | ✅ |
| `user_id` for signature load/save comes from the **decoded token**, never the client payload | ✅ `ws_user_id` in `websocket_endpoint` |

The frontend sends the JWT as `ws://…/ws/{id}?token=<jwt>`; the backend verifies
it and looks the user up before `accept()`. A rejected handshake surfaces as the
"Session not authorized" toast in the UI.

## CORS

| Check | Status |
|-------|--------|
| `access-control-allow-origin` is **`http://localhost:5173`**, never `*` | ✅ verified |
| A disallowed `Origin` is **not** reflected as allowed | ✅ verified |

Configured in `backend/main.py` via `CORSMiddleware(allow_origins=["http://localhost:5173"])`.

## Ownership checks

- Session endpoints (`/sessions/{id}/reps|end|detail|angles`) verify the workout
  belongs to the authenticated user (`_owned_workout` → 404 otherwise).
- Profile / common-errors / tempo-history endpoints reject access to another
  user's `{user_id}` (403).

## Note on the ML privacy posture

Raw video frames are decoded in memory, processed, and discarded — never written
to disk or any table (see `docs/privacy_notes.md`). Only numeric landmark data is
persisted, and that is under the 90-day TimescaleDB retention policy
(`docs/timescale_policy.md`).

## Not yet covered (future work)

- Rate limiting / brute-force protection on `/auth/login`.
- Token refresh / revocation (tokens are valid until `exp`; 24 h TTL).
- File-upload validation — N/A currently (no file-upload endpoints; frames arrive
  as base64 over the authenticated WS).
