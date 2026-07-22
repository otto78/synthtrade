from typing import Dict, Any, List
from fastapi import WebSocket

from app.scalping.models.backtest import BacktestResult
from app.scalping.engine.position_manager import PositionManager
from app.scalping.session_load_guard import SessionLoadGuard

# ---------------------------------------------------------------------------
# In-memory state (in production, use DB + Supabase)
# ---------------------------------------------------------------------------
_backtest_results: Dict[str, BacktestResult] = {}

# Shared execution state — will be populated at startup from main.py
_execution_state: Dict[str, Any] = {
    "loop": None,              # ExecutionLoop instance
    "position_manager": PositionManager(),
    "signal_engine": None,      # SignalScoreEngine instance
    "ws_client": None,          # WS client instance
    "ws_tasks": [],             # asyncio tasks for WS stream → broadcast
    "session": {
        "session_id": None,
        "status": "idle",
        "mode": "paper",
        "strategy": "scalping_v2",
        "symbol": "BTCUSDT",
        "started_at": None,
        "stopped_at": None,
        "paper_balance": 10000.0,
        "trade_value": 100.0,   # USD value per trade — set by user in UI
        "leverage": 1,         # leverage multiplier — set by user in UI (1=no margin)
    },
    "trade_history": [],        # List[dict] — trade history for performance calc
    "risk_config": {
        "max_daily_loss": 50,
        "max_drawdown": 10,
        "leverage": 10,
        "stop_loss_pct": 1.05,
        "take_profit_pct": 1.55,
    },
    "pending_live_close": False,  # set to True when a live BUY is executed
    "session_load_guard": SessionLoadGuard(),
}

# WebSocket connections
_scalping_ws_connections: List[WebSocket] = []


# ── Cache locale per conversione commissione BNB ──────────────────────────
# Previene il flood di chiamate API quando Binance è rate-limited.
# Il prezzo BNB/USDC viene aggiornato ogni 60s massimo.
_bnb_price_cache: Dict[str, Any] = {"price": 0.0, "timestamp": 0.0}
_bnb_price_cache_ttl = 60  # secondi — più lungo del TTL di get_ticker_price (15s)

# ── Log throttling: evita flood di warning identici ──────────────────────
# Traccia l'ultimo messaggio di warning per contesto, e sopprime duplicati
# ravvicinati (< 10s dallo stesso contesto).
_last_warning: Dict[str, float] = {}
_warning_throttle_sec = 10.0
