"""Performance endpoint: get trading performance metrics.

Extracted from rest/session.py (TASK-1166.E).
"""
import logging
from typing import Dict

from fastapi import APIRouter

from app.scalping._state import _execution_state
from app.scalping.config_loader import get_scalping_config

logger = logging.getLogger(__name__)

router = APIRouter()


def _calc_session_entry_and_hold(
    trade_history: list,
    current_price: float | None,
):
    """Calcola l'entry price del primo trade storico e il PnL % del buy-and-hold.

    Args:
        trade_history: Lista dei trade della sessione
        current_price: Prezzo corrente (ultima candela) per calcolare hold PnL
    
    Returns:
        tuple: (first_trade_entry, hold_pnl_pct) — None se non ci sono trade chiusi
    """
    closed = [t for t in trade_history if t.get("exit_price") is not None]
    if not closed:
        return None, None
    # Primo trade storico (più vecchio)
    oldest = sorted(closed, key=lambda t: t.get("timestamp", ""))[0]
    entry = oldest.get("entry_price")
    if entry is None or entry <= 0:
        return None, None
    if current_price is not None and current_price > 0:
        hold_pnl = ((current_price - entry) / entry) * 100
    else:
        hold_pnl = None
    return float(entry), round(hold_pnl, 2) if hold_pnl is not None else None


@router.get("/performance")
async def get_performance() -> Dict:
    """Get performance metrics from trade history."""
    # Only count completed (closed) trades — exclude open positions still in history
    trades = [t for t in _execution_state["trade_history"] if t.get("exit_price") is not None]

    if not trades:
        return {
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "win_rate": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "consecutive_losses": 0,
        }
    
    winning = [t for t in trades if (t.get("pnl") or 0) > 0]
    losing = [t for t in trades if (t.get("pnl") or 0) < 0]
    
    total_pnl = sum((t.get("pnl") or 0) for t in trades)
    win_count = len(winning)
    lose_count = len(losing)
    total = len(trades)
    
    avg_win = sum((t.get("pnl") or 0) for t in winning) / win_count if win_count else 0
    avg_loss = abs(sum((t.get("pnl") or 0) for t in losing) / lose_count) if lose_count else 0
    
    gross_profit = sum((t.get("pnl") or 0) for t in winning)
    gross_loss = abs(sum((t.get("pnl") or 0) for t in losing))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else 0
    
    # Calculate max drawdown from running equity
    running_pnl = 0.0
    base_balance = float(_execution_state["session"].get("paper_balance", 10000.0) or 10000.0)
    equity = base_balance
    peak_equity = base_balance
    max_dd_pct = 0.0
    for t in trades:
        running_pnl += (t.get("pnl") or 0)
        equity = base_balance + running_pnl
        if equity > peak_equity:
            peak_equity = equity
        if peak_equity > 0:
            dd_pct = (peak_equity - equity) / peak_equity
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
    
    # Consecutive losses
    cons_losses = 0
    max_cons_losses = 0
    for t in reversed(trades):
        if (t.get("pnl") or 0) < 0:
            cons_losses += 1
        else:
            break
    # Also calculate historical max consecutive losses
    current_run = 0
    for t in trades:
        if (t.get("pnl") or 0) < 0:
            current_run += 1
            max_cons_losses = max(max_cons_losses, current_run)
        else:
            current_run = 0
    
    session = _execution_state["session"]
    allocated_capital = float(session.get("trade_value") or 0)
    if allocated_capital <= 0:
        allocated_capital = float(session.get("paper_balance") or 10000.0)
    
    total_pnl_pct = (total_pnl / allocated_capital) * 100 if allocated_capital > 0 else 0

    # Hold PnL: how much we'd have made holding from first trade entry price
    loop = _execution_state.get("loop")
    current_price = None
    if loop and hasattr(loop, "_candle_buffer") and loop._candle_buffer and loop._candle_buffer.latest:
        current_price = float(loop._candle_buffer.latest.close)
    first_entry, hold_pnl_pct = _calc_session_entry_and_hold(
        _execution_state.get("trade_history", []),
        current_price,
    )

    # Signal strength threshold (variable, set by supervisor)
    try:
        signal_threshold = get_scalping_config().signal_strength_threshold
    except Exception:
        signal_threshold = None

    trading_beats_hold = None
    if hold_pnl_pct is not None:
        trading_beats_hold = total_pnl_pct >= hold_pnl_pct

    return {
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "win_rate": round(win_count / total * 100, 2) if total else 0,
        "total_trades": total,
        "winning_trades": win_count,
        "losing_trades": lose_count,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "profit_factor": profit_factor,
        "max_drawdown": max_dd_pct,
        "consecutive_losses": max_cons_losses,
        # Trading vs Hold comparison
        "hold_pnl_pct": round(hold_pnl_pct, 2) if hold_pnl_pct is not None else None,
        "trading_beats_hold": trading_beats_hold,
        # Signal threshold (for proximity indicator in Market Intel panel)
        "signal_strength_threshold": signal_threshold,
    }
