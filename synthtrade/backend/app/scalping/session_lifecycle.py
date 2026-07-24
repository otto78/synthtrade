import asyncio
import logging
from typing import Any, Dict

from app.scalping._state import _execution_state
from app.scalping.config_loader import get_scalping_config
from app.scalping.broadcast import broadcast_scalping_event

logger = logging.getLogger(__name__)

def _enrich_session_with_threshold(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add signal_strength_threshold to a session dict (if it's a copy)."""
    try:
        session_data["signal_strength_threshold"] = get_scalping_config().signal_strength_threshold
    except Exception:
        session_data["signal_strength_threshold"] = None
    return session_data


def _sync_session_load_guard() -> None:
    guard = _execution_state.get("session_load_guard")
    if guard:
        _execution_state["session"]["load_guard"] = guard.monitor_data


# ---------------------------------------------------------------------------
# Helper: wire WS client events → broadcast to scalping WS clients
# ---------------------------------------------------------------------------

async def _refresh_session_balance():
    """Refresh session live_balance from exchange (TASK-1107: provider-neutral)."""
    session = _execution_state["session"]
    if session["mode"] == "live" and _execution_state.get("exchange"):
        max_retries = 3
        retry_delay = 1.0
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                adapter = _execution_state["exchange"]
                symbol = session.get("symbol", "BTC-USD")

                # Derive quote asset from symbol (provider-neutral)
                from app.execution.exchange_models import SymbolRef
                try:
                    sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
                    quote = sym_ref.quote
                except Exception:
                    quote = "USD"

                # TASK-1107: use protocol method — works for OKX and Binance
                bal = await adapter.get_balance(quote)

                if bal is None or bal <= 0:
                    logger.warning(
                        "Session balance refresh found no preferred quote asset balance. Keeping previous live_balance=%s",
                        session.get("live_balance"),
                    )
                else:
                    session["live_balance"] = bal
                    logger.info(f"Session balance refreshed: {bal} {quote}")
                    enriched = _enrich_session_with_threshold(session.copy())
                    await broadcast_scalping_event("session_restored", enriched)
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Balance refresh attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
        logger.error(f"Balance refresh failed after {max_retries} attempts: {last_error}")
