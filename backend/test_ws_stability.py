"""Phase 9 — WebSocket stability + ConnectionManager leak test.

Two checks with real measured numbers:
  1. Network drop rate: connect (authenticated), send 1000 echo frames, count
     responses, assert < 1% dropped. Also reports throughput (frames/sec).
  2. ConnectionManager leak: 1000 connect/disconnect cycles in-process with a
     mock WebSocket; tracemalloc before/after; assert active_connections is empty
     and memory growth is bounded (no leak).

The network part needs the server running on :8000.
Run:  python backend/test_ws_stability.py
"""

import asyncio
import gc
import json
import os
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
import websockets  # noqa: E402

from backend.connection_manager import ConnectionManager  # noqa: E402

BASE = "http://localhost:8000"
EMAIL, PASSWORD = "wsstab@example.com", "pw12345"
N_FRAMES = 1000


def _token():
    c = httpx.Client(base_url=BASE, timeout=30)
    c.post("/auth/register", json={"name": "S", "email": EMAIL, "password": PASSWORD})
    tok = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    c.close()
    return tok


async def network_drop_test():
    tok = _token()
    uri = f"ws://localhost:8000/ws/stab?token={tok}"
    sent = received = 0
    start = time.perf_counter()
    async with websockets.connect(uri, max_queue=None) as ws:
        for i in range(N_FRAMES):
            await ws.send(json.dumps({"frame_id": i, "state": "UP"}))
            sent += 1
            while True:
                resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if resp.get("type") == "ping":          # heartbeat, not a frame
                    await ws.send(json.dumps({"type": "pong"}))
                    continue
                received += 1
                break
    elapsed = time.perf_counter() - start
    drop_rate = (sent - received) / sent * 100
    print(f"network: sent={sent} received={received} dropped={sent - received} "
          f"({drop_rate:.2f}%) in {elapsed:.1f}s -> {sent / elapsed:.0f} frames/sec")
    assert drop_rate < 1.0, f"drop rate {drop_rate:.2f}% >= 1%"
    return drop_rate


class _MockWS:
    async def accept(self):
        pass

    async def send_text(self, _):
        pass


async def connection_manager_leak_test():
    m = ConnectionManager()
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.take_snapshot()

    for i in range(N_FRAMES):
        sid = f"s{i}"
        await m.connect(_MockWS(), sid)
        m.disconnect(sid)

    gc.collect()
    after = tracemalloc.take_snapshot()
    growth = sum(s.size_diff for s in after.compare_to(before, "lineno"))
    tracemalloc.stop()

    print(f"leak: after {N_FRAMES} connect/disconnect cycles -> "
          f"active_connections={len(m.active_connections)}, "
          f"heap growth={growth / 1024:.1f} KB")
    assert m.active_connections == {}, "ConnectionManager leaked connections"
    assert growth < 200 * 1024, f"heap grew {growth} bytes — possible leak"


def main():
    asyncio.run(network_drop_test())
    asyncio.run(connection_manager_leak_test())
    print("\nPASS WebSocket stability + ConnectionManager leak")


if __name__ == "__main__":
    main()
