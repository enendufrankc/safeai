# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""WebSocket endpoint for real-time audit event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Manages WebSocket connections and broadcasts audit events."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, filters: dict[str, Any] | None = None) -> None:
        """Accept a WebSocket connection with optional subscription filters."""
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = filters or {}
        logger.info("WebSocket client connected (filters=%s)", filters)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self._connections.pop(websocket, None)
        logger.info("WebSocket client disconnected")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Send an event to all connected clients matching their filters."""
        async with self._lock:
            clients = list(self._connections.items())

        for ws, filters in clients:
            if ws.client_state != WebSocketState.CONNECTED:
                await self.disconnect(ws)
                continue
            if not self._matches_filters(event, filters):
                continue
            try:
                await ws.send_json(event)
            except Exception:
                await self.disconnect(ws)

    @staticmethod
    def _matches_filters(event: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if an event matches subscription filters."""
        if not filters:
            return True
        if "boundary" in filters and event.get("boundary") != filters["boundary"]:
            return False
        if "agent_id" in filters and event.get("agent_id") != filters["agent_id"]:
            return False
        if "policy_name" in filters and event.get("policy_name") != filters["policy_name"]:
            return False
        return True

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Global broadcaster instance
broadcaster = EventBroadcaster()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint handler: ws://host:port/v1/ws/events

    Clients can send a JSON filter message after connecting:
    {"boundary": "input", "agent_id": "my-agent"}

    Then receive matching audit events in real-time.
    """
    filters: dict[str, Any] = {}

    # Parse query params as initial filters
    for key in ("boundary", "agent_id", "policy_name"):
        val = websocket.query_params.get(key)
        if val:
            filters[key] = val

    await broadcaster.connect(websocket, filters)
    try:
        while True:
            # Listen for filter updates from client
            data = await websocket.receive_text()
            try:
                new_filters = json.loads(data)
                if isinstance(new_filters, dict):
                    async with broadcaster._lock:
                        broadcaster._connections[websocket] = new_filters
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.disconnect(websocket)


def register_websocket_routes(app: Any) -> None:
    """Attach websocket routes to app (kept for backward compatibility)."""
    return None
