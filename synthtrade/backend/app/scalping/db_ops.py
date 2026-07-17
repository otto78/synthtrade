import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.db.supabase_client import get_supabase
from app.scalping._state import _execution_state
from app.config import settings

logger = logging.getLogger(__name__)


async def _save_open_position_to_db(pos, db_session_id: str,
                                    tp_price: float = 0.0, sl_price: float = 0.0,
                                    supervisor_context: Optional[Dict[str, Any]] = None,
                                    signal_log_id: Optional[str] = None):
    """Save opened position to Supabase with status='open' and no exit/pnl yet.
    Called immediately after pm.open_position() to persist the current trade
    so session restore can pick it up after restart.
    Includes tp_price, sl_price, oco_order_list_id, sl_order_id, tp_order_id (TASK-825).
    """
    try:
        def _db_op():
            supabase = get_supabase()
            
            insert_data = {
                "session_id": db_session_id,
                "symbol": pos.symbol,
                "side": pos.side,
                "entry_price": round(float(pos.entry_price), 2),
                "exit_price": None,
                "quantity": float(pos.quantity),
                "pnl": None,
                "pnl_pct": None,
                "strategy_type": _execution_state["session"].get("strategy", "unknown"),
                "signal_reason": "entry",
                "status": "open",
                "entry_time": pos.entry_time.isoformat() if pos.entry_time else datetime.now(timezone.utc).isoformat(),
                "exit_time": None,
                "tp_price": tp_price if tp_price else None,
                "sl_price": sl_price if sl_price else None,
                # TASK-1108: provider-neutral order ids
                "exchange_provider": settings.EXCHANGE_PROVIDER.lower(),
                "exchange_order_id": getattr(pos, 'entry_order_id', None),
                "exchange_bracket_id": pos.oco_order_list_id,   # OKX: algoId; Binance: orderListId
                "exchange_tp_order_id": pos.tp_order_id,
                "exchange_sl_order_id": pos.sl_order_id,
                # Legacy Binance columns (kept for backward compat)
                "oco_order_list_id": pos.oco_order_list_id,
                "sl_order_id": pos.sl_order_id,
                "tp_order_id": pos.tp_order_id,
            }
            if signal_log_id:
                insert_data["signal_log_id"] = signal_log_id
            if supervisor_context:
                insert_data.update({
                    "btc_price_at_entry": supervisor_context.get("btc_price_at_entry"),
                    "btc_change_1h_pct": supervisor_context.get("btc_change_1h_pct"),
                    "btc_change_24h_pct": supervisor_context.get("btc_change_24h_pct"),
                    "macro_regime": supervisor_context.get("macro_regime"),
                    "signal_price": supervisor_context.get("signal_price"),
                    "slippage_pct": supervisor_context.get("slippage_pct"),
                    "signal_to_fill_ms": supervisor_context.get("signal_to_fill_ms"),
                    "strategies_considered": supervisor_context.get("strategies_considered"),
                    "strategy_rejection_reason": supervisor_context.get("strategy_rejection_reason"),
                    "regime_classified": supervisor_context.get("regime_classified"),
                    "candlestick_pattern": supervisor_context.get("candlestick_pattern"),
                    "volume_anomaly": supervisor_context.get("volume_anomaly"),
                    "support_resistance_data": supervisor_context.get("support_resistance_data"),
                })
            
            supabase.table("scalping_trades").insert(insert_data).execute()
        await asyncio.to_thread(_db_op)
    except Exception as db_e:
        logger.warning(f"Failed to save open position to DB: {db_e}")


async def _update_closed_position_in_db(pos, close_price: float, pnl: float, pnl_pct: float, reason: str):
    """Update the open position row in DB to 'closed' with exit price and PnL.
    
    FIX-2026-06-21: Strategy 1 uses oco_order_list_id (univoco per trade, match deterministico).
    Strategy 2 (fallback) uses session_id + entry_price + entry_time for pre-OCO-ID trades.
    """
    try:
        db_sid = _execution_state["session"].get("db_session_id")
        if not db_sid:
            return
        def _db_op():
            supabase = get_supabase()
            trade_id = None
            # Pre-compute fallback values (used in Strategy 2 and extrema ratio)
            entry_price_rounded = round(float(pos.entry_price), 2)
            entry_time_str = pos.entry_time.isoformat() if pos.entry_time else None
            
            # ── Strategy 1: match via oco_order_list_id (univoco, deterministico) ──
            if pos.oco_order_list_id:
                resp = supabase.table("scalping_trades") \
                    .select("id") \
                    .eq("oco_order_list_id", pos.oco_order_list_id) \
                    .eq("status", "open") \
                    .limit(1) \
                    .execute()
                if resp.data:
                    trade_id = resp.data[0]["id"]
            
            # ── Strategy 2 (fallback): session_id + entry_price + entry_time ──
            # Usato per trade pre-TASK-825 che non hanno oco_order_list_id.
            # Arrotonda entry_price a 2 decimali per evitare mismatch floating-point.
            if not trade_id:
                # Strategy 2a: session_id + entry_price + status (no entry_time string compare
                # to avoid Supabase timestamptz normalization mismatch)
                resp = supabase.table("scalping_trades") \
                    .select("id, entry_time") \
                    .eq("session_id", db_sid) \
                    .eq("entry_price", entry_price_rounded) \
                    .eq("status", "open") \
                    .limit(1) \
                    .execute()
                if resp.data:
                    trade_id = resp.data[0]["id"]

            # Strategy 2b: if still not found, try with entry_time range ±2s
            if not trade_id and entry_time_str and pos.entry_time:
                from datetime import timedelta
                t_low = (pos.entry_time - timedelta(seconds=2)).isoformat()
                t_high = (pos.entry_time + timedelta(seconds=2)).isoformat()
                resp = supabase.table("scalping_trades") \
                    .select("id") \
                    .eq("session_id", db_sid) \
                    .eq("status", "open") \
                    .gte("entry_time", t_low) \
                    .lte("entry_time", t_high) \
                    .limit(1) \
                    .execute()
                if resp.data:
                    trade_id = resp.data[0]["id"]
            
            if trade_id:
                # UPDATE — modifica la riga 'open' esistente
                supabase.table("scalping_trades").update({
                    "exit_price": close_price,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "signal_reason": reason,
                    "status": "closed",
                    "exit_time": datetime.now(timezone.utc).isoformat(),
                }).eq("id", trade_id).execute()
                logger.debug(f"DB position closed (match via {'oco_order_list_id' if pos.oco_order_list_id else 'fallback'}): trade_id={trade_id}")
            else:
                # Fallback extrema ratio: insert new row if no open row found
                logger.warning(f"No open row found for close: session={db_sid} symbol={pos.symbol} entry_price={entry_price_rounded} entry_time={entry_time_str} — inserting as new row")
                supabase.table("scalping_trades").insert({
                    "session_id": db_sid,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": round(float(pos.entry_price), 2),
                    "exit_price": close_price,
                    "quantity": float(pos.quantity),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "strategy_type": _execution_state["session"].get("strategy", "unknown"),
                    "signal_reason": reason,
                    "status": "closed",
                    "entry_time": pos.entry_time.isoformat(),
                    "exit_time": datetime.now(timezone.utc).isoformat(),
                    # TASK-1108: provider-neutral fields
                    "exchange_provider": settings.EXCHANGE_PROVIDER.lower(),
                    "exchange_bracket_id": pos.oco_order_list_id,
                    "exchange_tp_order_id": pos.tp_order_id,
                    "exchange_sl_order_id": pos.sl_order_id,
                    # Legacy
                    "oco_order_list_id": pos.oco_order_list_id,
                }).execute()
        await asyncio.to_thread(_db_op)
    except Exception as db_e:
        logger.warning(f"Failed to update closed position in DB: {db_e}")
