import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Set


logger = logging.getLogger(__name__)


class SessionLoadGuard:
    """State manager that blocks trade generation until a scalping session is fully loaded."""

    REQUIRED_PHASES: Set[str] = {
        "db_phase",
        "exchange_phase",
        "position_phase",
        "buffer_phase",
        "pipeline_phase",
    }

    def __init__(self) -> None:
        self._state = "idle"
        self._phases_completed: Set[str] = set()
        self._loading_started_at: float | None = None
        self._error: str | None = None
        self._ready_event = asyncio.Event()
        self._max_timeout_sec = 30.0
        self._trade_attempts_during_load: deque[Dict[str, Any]] = deque(maxlen=100)
        self._blocked_attempts = 0

    def reset(self) -> None:
        self._state = "idle"
        self._phases_completed.clear()
        self._loading_started_at = None
        self._error = None
        self._ready_event.clear()
        self._trade_attempts_during_load.clear()
        self._blocked_attempts = 0

    def start_loading(self) -> None:
        self._state = "loading"
        self._loading_started_at = time.monotonic()
        self._phases_completed.clear()
        self._ready_event.clear()
        self._error = None
        self._trade_attempts_during_load.clear()
        self._blocked_attempts = 0

    def _get_elapsed(self) -> float:
        if self._loading_started_at is None:
            return 0.0
        return time.monotonic() - self._loading_started_at

    def _check_timeout(self) -> None:
        if self._loading_started_at and self._state == "loading":
            elapsed = self._get_elapsed()
            if elapsed > self._max_timeout_sec:
                self._state = "failed"
                self._error = (
                    f"Session loading timeout after {elapsed:.1f}s "
                    f"(max={self._max_timeout_sec}s). "
                    f"Phases: {sorted(self._phases_completed)}"
                )
                self._ready_event.clear()
                logger.error("[SESSION_LOCK] %s", self._error)
            elif elapsed > 0 and int(elapsed) % 5 == 0 and elapsed - int(elapsed) < 0.5:
                logger.warning(
                    "[SESSION_LOCK] Session still loading after %.0fs — phases completed: %s",
                    elapsed,
                    sorted(self._phases_completed),
                )

    def complete_phase(self, phase: str) -> None:
        if self._state in {"ready", "failed"}:
            return

        self._phases_completed.add(phase)
        self._check_timeout()
        if self._state == "failed":
            return

        if self.REQUIRED_PHASES.issubset(self._phases_completed):
            self._state = "ready"
            self._ready_event.set()
            logger.warning(
                "\033[92m*** [SESSION_LOCK] Session READY after %.1fs — all phases complete ***\033[0m",
                self._get_elapsed(),
            )

    def is_ready(self) -> bool:
        return self._state == "ready" and self._ready_event.is_set()

    def record_trade_attempt(self, symbol: str, source: str) -> None:
        self._check_timeout()
        elapsed = self._get_elapsed()
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": round(elapsed, 3),
            "symbol": symbol,
            "source": source,
        }
        self._trade_attempts_during_load.append(entry)
        self._blocked_attempts += 1
        logger.warning(
            "[SESSION_LOCK] Trade attempt BLOCKED (%s): %s | total blocked: %d",
            source,
            entry,
            self._blocked_attempts,
        )

    def fail(self, error: str) -> None:
        if self._state in {"ready", "failed"}:
            return
        self._state = "failed"
        self._error = error
        self._ready_event.clear()
        logger.error("[SESSION_LOCK] %s", error)

    @property
    def monitor_data(self) -> Dict[str, Any]:
        self._check_timeout()
        return {
            "state": self._state,
            "ready": self.is_ready(),
            "elapsed_sec": round(self._get_elapsed(), 3),
            "phases_completed": sorted(self._phases_completed),
            "required_phases": sorted(self.REQUIRED_PHASES),
            "missing_phases": sorted(self.REQUIRED_PHASES - self._phases_completed),
            "error": self._error,
            "blocked_attempts": self._blocked_attempts,
            "recent_blocked_attempts": list(self._trade_attempts_during_load),
        }
