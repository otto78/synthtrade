"""Broadcast helpers for scalping WebSocket clients.

Extracted from router.py (TASK-1166.D) to break circular import:
market_processors.py → broadcast.py instead of market_processors.py → router.py.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.scalping._state import (
    _execution_state,
    _scalping_ws_connections,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def broadcast_scalping_event(event_type: str, payload: Any):
    """Broadcast an event to all connected scalping WebSocket clients."""
    # TASK-1255: Stop & Go — inject restart_countdown into session_restored payloads
    if event_type == "session_restored" and isinstance(payload, dict) and payload.get("auto_restart_weekly") and payload.get("status") == "running":
        try:
            from app.scalping.session_auto_restart import get_restart_countdown
            payload["restart_countdown"] = get_restart_countdown(payload)
        except Exception:
            pass
    message = {
        "type": event_type,
        "payload": payload,
        "timestamp": _now(),
    }
    snapshot = list(_scalping_ws_connections)
    dead = []
    for ws in snapshot:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            _scalping_ws_connections.remove(ws)
        except ValueError:
            pass  # already removed by disconnect handler
    # Always store last error in session state for HTTP response fallback
    if event_type == "error":
        session = _execution_state["session"]
        session["last_error"] = {"code": payload.get("code"), "message": payload.get("message"), "timestamp": message["timestamp"]}
