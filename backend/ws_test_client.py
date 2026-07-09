"""TRACK B — Standalone WebSocket test client (Phase 4).

Proves the send/receive round-trip and the heartbeat before any React work.
Connects, sends one fake frame, prints the server's response, then waits for
the server's 10s idle ping and replies with a pong.

Run (server must be running first):
    python backend/ws_test_client.py
"""

import asyncio
import json

import websockets

URI = "ws://localhost:8000/ws/test123"


async def main():
    async with websockets.connect(URI) as ws:
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
