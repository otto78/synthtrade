"""Position endpoints: get current position, list all positions.

Extracted from rest/session.py (TASK-1166.E).
"""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter

from app.scalping._state import _execution_state
from app.scalping.pricing import (
    _get_fee_rate,
    _net_to_gross_pct,
    _sl_price_from_entry,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/position")
async def get_position() -> Optional[Dict]:
    """Get current open position from PositionManager."""
    pm = _execution_state["position_manager"]
    pos = pm.get_open()
    if not pos:
        return None
    
    # Calculate current PnL estimate
    entry = float(pos.entry_price)
    loop = _execution_state.get("loop")
    if loop and hasattr(loop, "_candle_buffer") and len(loop._candle_buffer) > 0:
        candles = loop._candle_buffer.get()
        current_price = float(candles[-1].close)
        qty = float(pos.quantity)
        entry_val = entry * qty
        current_val = current_price * qty
        gross_pnl = (current_price - entry) * qty if pos.side == "BUY" else (entry - current_price) * qty
        
        # TASK-884: Usa fee tier per PnL non realizzato (Caso B)
        # Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
        if pos.entry_commission is not None and pos.entry_commission > 0:
            entry_commission = float(pos.entry_commission)
            # Converti BNB to USDC se necessario
            if pos.entry_commission_asset == "BNB":
                # Non possiamo chiamare exchange qui (endpoint sincrono), assumiamo conversione manuale o valore salvato
                # Per ora usiamo il valore come è (dovrebbe essere già convertito o in USDC)
                entry_commission = entry_commission
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
    else:
        current_price = float(pos.entry_price)
        pnl = 0.0
        pnl_pct = 0.0
    
    # TASK-885: Calcola target netti TP/SL per endpoint REST
    risk_cfg = _execution_state.get("risk_config", {})
    sl_pct = float(risk_cfg.get("stop_loss_pct", 0.3))
    tp_pct = float(risk_cfg.get("take_profit_pct", 0.5))
    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
    exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market order (taker)
    fee_round_trip = (entry_fee_rate + exit_fee_rate) * 100  # converti in percentuale
    
    # Calcola percentuali nette (sottrai fee round-trip dai target lordi)
    sl_pct_net = sl_pct - fee_round_trip  # perdita netta è peggiore
    tp_pct_net = tp_pct - fee_round_trip  # guadagno netto è minore

    # TASK-1129: veri prezzi TP/SL piazzati su OKX (fallback a ricalcolo da pct
    # per posizioni pre-fix / restore senza questi campi).
    _ef_p = _get_fee_rate(fee_tier, "taker", 0.001)
    _xf_p = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market (taker)
    # TASK-1127: Fees are now positive for base level accounts
    sl_price_calc = _sl_price_from_entry(entry, pos.side, sl_pct, _ef_p, _xf_p)[0]
    tp_price_calc = entry * (1 + _net_to_gross_pct(tp_pct, _ef_p, _xf_p) / 100) if pos.side == "BUY" else entry * (1 - _net_to_gross_pct(tp_pct, _ef_p, _xf_p) / 100)
    stop_loss_price = float(pos.sl_price) if pos.sl_price is not None else sl_price_calc
    take_profit_price = float(pos.tp_price) if pos.tp_price is not None else tp_price_calc

    return {
        "symbol": pos.symbol,
        "side": pos.side,
        "entry_price": float(pos.entry_price),
        "current_price": current_price,
        "quantity": float(pos.quantity),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "status": pos.status.value,
        "entry_time": pos.entry_time.isoformat(),
        "stop_loss_pct": sl_pct,
        "take_profit_pct": tp_pct,
        "stop_loss_pct_net": round(sl_pct_net, 2),  # TASK-885
        "take_profit_pct_net": round(tp_pct_net, 2),  # TASK-885
        "stop_loss_price": round(stop_loss_price, 2),  # TASK-1129
        "take_profit_price": round(take_profit_price, 2),  # TASK-1129
        "breakeven_pct": round(fee_round_trip, 2),
    }


@router.get("/position/list")
async def list_positions() -> List[Dict]:
    """List all positions from PositionManager."""
    pm = _execution_state["position_manager"]
    positions = pm.get_all()
    return [
        {
            "symbol": p.symbol,
            "side": p.side,
            "entry_price": float(p.entry_price),
            "quantity": float(p.quantity),
            "status": p.status.value,
            "entry_time": p.entry_time.isoformat(),
        }
        for p in positions
    ]
