"""TRACK B — WebSocket connection registry (Phase 4).

Tracks one live WebSocket per session_id so the server can push processed pose
frames to the right client, and clean up ghost connections on disconnect.
"""

import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_to_session(self, data: dict, session_id: str):
        websocket = self.active_connections.get(session_id)
        if websocket is not None:
            await websocket.send_text(json.dumps(data))
