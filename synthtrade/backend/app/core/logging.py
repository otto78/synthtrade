import logging
import sys


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

    formatter = _ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

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
    formatter = _ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers.clear()
        lib_logger.setLevel(logging.WARNING)
        lib_logger.addHandler(handler)
        lib_logger.propagate = False