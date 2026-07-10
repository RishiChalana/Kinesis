"""TRACK B — Standalone WebSocket test client (Phase 4, auth-updated Phase 9).

Proves the send/receive round-trip and the heartbeat before any React work.
As of Phase 9 the WS requires a JWT (query param), so this registers/logs in a
throwaway user first, then connects with ?token=...

Run (server must be running first):
    python backend/ws_test_client.py
"""

import asyncio
import json
import urllib.error
import urllib.request

import websockets

BASE = "http://localhost:8000"
EMAIL, PASSWORD = "wsclient@example.com", "pw12345"


def _http(method, path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or "null")


def _get_token():
    _http("POST", "/auth/register", {"name": "WS", "email": EMAIL, "password": PASSWORD})
    return _http("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})["access_token"]


async def main():
    token = _get_token()
    uri = f"ws://localhost:8000/ws/test123?token={token}"
    async with websockets.connect(uri) as ws:
        # 1) Send a fake frame and print the echoed schema message.
        fake_frame = {
            "frame_id": 1,
            "timestamp": 1732200000.0,
            "rep_count": 3,
            "state": "DOWN",
            "left_angle": 88.5,
            "right_angle": 91.2,
        }
        await ws.send(json.dumps(fake_frame))
        response = await ws.recv()
        print("round-trip response:", response)

        # 2) Stay idle and wait for the server's heartbeat ping (~10s).
        print("waiting up to 12s for heartbeat ping...")
        ping = await asyncio.wait_for(ws.recv(), timeout=12)
        print("heartbeat received:", ping)

        # 3) Reply with a pong to keep the connection alive.
        await ws.send(json.dumps({"type": "pong"}))
        print("sent pong — connection kept alive, round-trip + heartbeat OK")


if __name__ == "__main__":
    asyncio.run(main())
