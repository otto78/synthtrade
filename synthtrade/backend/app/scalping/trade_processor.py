"""Trade processor: consume trade_queue, broadcast to frontend, update PnL, feed CVD.

Extracted from market_processors.py (TASK-1166.D).
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.scalping._state import _execution_state
from app.scalping.pricing import (
    _get_fee_rate,
    _sl_price_from_entry,
    _net_to_gross_pct,
    _convert_bnb_commission_to_usdc,
)
from app.scalping.trade_executor import _close_position_and_record
from app.scalping.session_lifecycle import _sync_session_load_guard
from app.scalping.broadcast import broadcast_scalping_event

logger = logging.getLogger(__name__)


async def _trade_processor(symbol: str, restore_mode: bool = False):
    """Consume trade_queue and broadcast + update PnL + feed CVD."""
    _cvd = _execution_state.get("cvd_calculator")
    while _execution_state["session"]["status"] != "idle":
        _ws_ref = _execution_state.get("ws_client")
        if _ws_ref is None or _ws_ref._stop_event.is_set():
            await asyncio.sleep(0.1)
            continue
        try:
            event = await asyncio.wait_for(_ws_ref.trade_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            if _execution_state["session"]["status"] == "idle":
                break
            continue

        try:
            guard = _execution_state.get("session_load_guard")
            if guard and not guard.is_ready():
                guard.record_trade_attempt(event.symbol, "trade_processor")
                _sync_session_load_guard()
                continue

            # Feed CVD calculator with real-time trade pressure
            if _cvd is not None:
                try:
                    _cvd.on_trade(event.price, event.quantity, event.is_buyer_maker)
                except Exception:
                    pass  # Non-blocking

            # Broadcast to frontend WS clients
            await broadcast_scalping_event("trade", {
                "symbol": event.symbol,
                "price": event.price,
                "quantity": event.quantity,
                "is_buyer_maker": event.is_buyer_maker,
                "timestamp": datetime.fromtimestamp(event.timestamp / 1000, tz=timezone.utc).isoformat(),
            })

            # Update position PnL if there's an open position
            pm = _execution_state["position_manager"]
            pos = pm.get_open()
            if pos and pos.symbol.lower() == event.symbol.lower():
                entry = float(pos.entry_price)
                current = event.price
                qty = float(pos.quantity)
                entry_val = entry * qty
                current_val = current * qty
                
                risk_cfg = _execution_state.get("risk_config", {})
                _sl_cfg4 = float(risk_cfg.get("stop_loss_pct", 0.3))
                _tp_cfg4 = float(risk_cfg.get("take_profit_pct", 0.5))
                _ft4 = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                _ef4, _xf4 = _get_fee_rate(_ft4, "taker", 0.001), _get_fee_rate(_ft4, "maker", 0.001)
                # TASK-1127: Fees are now positive for base level accounts
                sl = _sl_price_from_entry(entry, pos.side, _sl_cfg4, _ef4, _xf4)[0]
                tp = entry * (1 + _net_to_gross_pct(_tp_cfg4, _ef4, _xf4) / 100) if pos.side == "BUY" else entry * (1 - _net_to_gross_pct(_tp_cfg4, _ef4, _xf4) / 100)
                # TASK-1129: usa i veri prezzi TP/SL piazzati su OKX se disponibili
                # (fallback al ricalcolo da percentuali per posizioni pre-fix / restore).
                if pos.sl_price is not None:
                    sl = float(pos.sl_price)
                if pos.tp_price is not None:
                    tp = float(pos.tp_price)
                
                gross_pnl = (current - entry) * qty if pos.side == "BUY" else (entry - current) * qty
                
                # TASK-883: Usa fee tier per PnL non realizzato (Caso B)
                # Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
                if pos.entry_commission is not None and pos.entry_commission > 0:
                    entry_commission = float(pos.entry_commission)
                    # Converti BNB to USDC se necessario
                    exchange = _execution_state.get("exchange")
                    if pos.entry_commission_asset == "BNB" and exchange:
                        entry_commission = await _convert_bnb_commission_to_usdc(
                            exchange, entry_commission, context="Trade processor: "
                        )
                else:
                    # Fallback: usa fee tier per entrata (costo atteso)
                    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                    entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
                    entry_commission = entry_val * entry_fee_rate
                
                # Exit: usa fee tier (costo di chiusura atteso al tier corrente)
                fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market order (taker)
                exit_commission = current_val * exit_fee_rate
                
                total_fees = entry_commission + exit_commission
                pnl = gross_pnl - total_fees
                pnl_pct = (pnl / entry_val) * 100
                await broadcast_scalping_event("position_update", {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "position_side": "SHORT" if pos.side == "SELL" else "LONG",
                    "entry_price": entry,
                    "current_price": current,
                    "quantity": qty,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "stop_loss_price": round(sl, 2),
                    "take_profit_price": round(tp, 2),
                    "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                    "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                    "breakeven_pct": round((_get_fee_rate(fee_tier, "taker", 0.001) + _get_fee_rate(fee_tier, "taker", 0.001)) * 100, 2),
                })
                
                # Execute SL/TP Auto Close — TASK-855: solo in paper mode
                # In live mode, SL/TP sono gestiti esclusivamente da OCO Binance via UDS (_on_order_update).
                # Eseguire close software in live causerebbe doppia vendita (software + OCO).
                hit_sl = (pos.side == "BUY" and current <= sl) or (pos.side == "SELL" and current >= sl)
                hit_tp = (pos.side == "BUY" and current >= tp) or (pos.side == "SELL" and current <= tp)
                _mode_trade = _execution_state["session"].get("mode", "paper")
                if _mode_trade != "live":
                    try:
                        if hit_sl:
                            await _close_position_and_record(pm, current, pos, reason="stop_loss")
                        elif hit_tp:
                            await _close_position_and_record(pm, current, pos, reason="take_profit")
                    except Exception as auto_close_err:
                        logger.error(f"Auto-close failed in _trade_processor: {auto_close_err}")
        except Exception as outer_trade_e:
            logger.error(f"Error in _trade_processor body: {outer_trade_e}", exc_info=True)
