"""Intelligence processor: poll intelligence and broadcast to frontend.

Also contains restore_mode_post_start helper.

Extracted from market_processors.py (TASK-1166.D).
"""
import asyncio
import logging

from app.config import settings
from app.scalping._state import _execution_state
from app.scalping.broadcast import broadcast_scalping_event
from app.scalping.rest.market_data import _snapshot_to_dict
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def _intelligence_processor(symbol: str, restore_mode: bool = False):
    """Poll intelligence and broadcast."""
    while _execution_state["session"]["status"] != "idle":
        _ws_ref = _execution_state.get("ws_client")
        if _ws_ref is None or _ws_ref._stop_event.is_set():
            await asyncio.sleep(0.1)
            continue
        try:
            snapshot = await _execution_state.get('signal_engine').get_snapshot()
            intel_data = _snapshot_to_dict(symbol, snapshot)
            await broadcast_scalping_event("intelligence", intel_data)
            
            # Save to Supabase market_intel_snapshots table
            try:
                def _db_op():
                    supabase = get_supabase()
                    supabase.table("market_intel_snapshots").insert({
                        "symbol": symbol,
                        "funding_rate": intel_data.get("funding_rate"),
                        "open_interest": intel_data.get("open_interest"),
                        "long_pct": intel_data.get("long_pct"),
                        "short_pct": intel_data.get("short_pct"),
                        "cvd_trend": intel_data.get("cvd_trend"),
                        "fear_greed_value": intel_data.get("fear_greed_value"),
                        "fear_greed_label": intel_data.get("fear_greed_label"),
                        "signal_score": intel_data.get("signal_score"),
                        "signal_bias": intel_data.get("signal_bias")
                    }).execute()
                await asyncio.to_thread(_db_op)
            except Exception as db_e:
                logger.warning(f"Failed to insert intelligence in DB: {db_e}")

        except Exception as e:
            logger.warning(f"Intelligence broadcast error: {e}")
        await asyncio.sleep(10.0)

async def restore_mode_post_start(symbol: str) -> None:
    """Post-start actions for restore_mode: start SupervisorScheduler + UDS if needed.

    Called from pipeline.py after processor tasks are spawned.
    For normal start, SupervisorScheduler is started in control_session's _start_with_error_logging.
    """
    try:
        from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler
        from app.scalping.trade_executor import _start_uds_if_needed
        signal_engine = _execution_state.get("signal_engine")
        supervisor = SupervisorScheduler(
            symbol=symbol,
            interval_seconds=settings.scalping.SCALPING_SUPERVISOR_INTERVAL_SEC,
            score_engine=signal_engine,
        )
        _execution_state["loop"].session_id = _execution_state["session"].get("db_session_id")
        supervisor.set_execution_loop(_execution_state["loop"])
        supervisor.start()
        _execution_state["supervisor_scheduler"] = supervisor
        logger.info(f"SupervisorScheduler started for {symbol} (restore_mode)")
    except Exception as e:
        logger.warning(f"Failed to start SupervisorScheduler in restore_mode: {e}")

    # avvia UDS se c'è una posizione aperta (TASK-827/TASK-830)
    pm = _execution_state["position_manager"]
    if pm.has_open() and _execution_state["session"].get("mode") == "live":
        try:
            await _start_uds_if_needed()
            logger.info(f"UDS avviato in restore_mode per posizione aperta su {symbol}")
        except Exception as uds_e:
            logger.warning(f"Failed to start UDS in restore_mode: {uds_e}")
