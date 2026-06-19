"""Circuit breaker per i collector HTTP dell'intelligence layer.

Dopo FAILURE_THRESHOLD errori consecutivi il collector viene disabilitato
per RESET_AFTER_SEC secondi (stato 'open'), poi tenta recovery in 'half_open'.
"""
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CollectorCircuitBreaker:
    FAILURE_THRESHOLD = 3
    RESET_AFTER_SEC = 300  # 5 minuti

    def __init__(self, name: str):
        self.name = name
        self._failures = 0
        self._state = "closed"  # closed | open | half_open
        self._opened_at: Optional[float] = None

    def _try_reset(self) -> None:
        if self._state == "open" and self._opened_at:
            if time.monotonic() - self._opened_at >= self.RESET_AFTER_SEC:
                self._state = "half_open"
                logger.info(f"[CB:{self.name}] half_open — attempting recovery")

    def is_available(self) -> bool:
        self._try_reset()
        return self._state in ("closed", "half_open")

    def on_success(self) -> None:
        if self._state == "half_open":
            logger.info(f"[CB:{self.name}] closed — recovered")
        self._failures = 0
        self._state = "closed"
        self._opened_at = None

    def on_failure(self) -> None:
        self._failures += 1
        if self._state == "half_open" or self._failures >= self.FAILURE_THRESHOLD:
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.warning(
                f"[CB:{self.name}] open — disabled for {self.RESET_AFTER_SEC}s "
                f"(failures={self._failures})"
            )
