import logging
import sys
from typing import ClassVar, Optional
from threading import Lock


class SessionContextFilter(logging.Filter):
    """Inietta session_id in ogni record di log quando una sessione è attiva.

    Usage:
        from app.core.logging import SessionContextFilter
        SessionContextFilter.set_session_id("sess_a1b2c3d4")

    Formato output record:
        con sessione:  "2026-06-24 10:30:00,123 [DEBUG] [sess_a1b2c3d4] logger.name: msg"
        senza sessione: "2026-06-24 10:30:00,123 [DEBUG] logger.name: msg"
    """

    _session_id: ClassVar[Optional[str]] = None
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def set_session_id(cls, session_id: str | None) -> None:
        """Set the active session_id (None to clear)."""
        with cls._lock:
            cls._session_id = session_id

    @classmethod
    def get_session_id(cls) -> str | None:
        with cls._lock:
            return cls._session_id

    def filter(self, record: logging.LogRecord) -> bool:
        with self._lock:
            sid = self._session_id
        record.session_id = f" [{sid}]" if sid else ""  # type: ignore[attr-defined]
        return True


# Format string: %(session_id)s renders as " [sess_xxx]" or ""
SESSION_FORMAT = "%(asctime)s [%(levelname)s]%(session_id)s %(name)s: %(message)s"


class _ColorFormatter(logging.Formatter):
    """Formatter con colori ANSI: ERROR=rosso, WARNING=giallo, INFO=default."""

    _RED = "\033[31m"
    _YELLOW = "\033[33m"
    _RESET = "\033[0m"
    _BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        if record.levelno >= logging.ERROR:
            return f"{self._RED}{formatted}{self._RESET}"
        if record.levelno >= logging.WARNING:
            return f"{self._YELLOW}{formatted}{self._RESET}"
        return formatted


def setup_logging():
    # Ensure stdout uses UTF-8 encoding for Unicode characters like emojis
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except AttributeError:
        pass  # Some environments (e.g., test runners) may not support reconfigure

    formatter = _ColorFormatter(SESSION_FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Attach SessionContextFilter to the handler so all log records
    # get the session_id field injected automatically.
    handler.addFilter(SessionContextFilter())

    # Root logger: everything goes through our handler
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )

    # ── FIX: Ensure scalping router logs appear even if imported before setup ──
    # On Windows with uvicorn, loggers created before basicConfig may not
    # propagate correctly. Force-add the handler to key modules.
    for forced_logger_name in (
        "app.scalping.router",
        "app.scalping.engine.execution_loop",
        "app.scalping.engine.signal_aggregator",
        "app.scalping.engine.ws_client",
        "app.scalping.intelligence.signal_score_engine",
    ):
        forced_logger = logging.getLogger(forced_logger_name)
        forced_logger.handlers.clear()
        forced_logger.addHandler(handler)
        forced_logger.setLevel(logging.INFO)
        forced_logger.propagate = False  # Avoid duplicate via root

    # Silence/standardize third-party loggers that use their own format
    for logger_name in (
        "httpx",
        "apscheduler",
        "uvicorn",
        "uvicorn.error",
        "watchfiles",
        "asyncio",
    ):
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers.clear()
        lib_logger.setLevel(logging.WARNING)
        lib_logger.propagate = True  # Let root handler format them

    # uvicorn.access: suppress the built-in access log (it re-creates its own
    # CustomFormatter after lifespan), route HTTP request logs through our app loggers instead.
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.setLevel(logging.WARNING)
    uvicorn_access.propagate = False


def reconfigure_uvicorn_loggers():
    """Post-lifespan hook: override uvicorn loggers that recreate their handlers
    after lifespan setup completes."""
    formatter = _ColorFormatter(SESSION_FORMAT)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SessionContextFilter())

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers.clear()
        lib_logger.setLevel(logging.WARNING)
        lib_logger.addHandler(handler)
        lib_logger.propagate = False