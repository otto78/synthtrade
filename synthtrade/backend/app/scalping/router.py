"""API Router per moduli Scalping (TASK-808, TASK-809, TASK-810).

Endpoints:
- POST /scalping/backtest/run                       — avvia backtest
- GET  /scalping/backtest/{id}/result               — recupera risultato backtest
- GET  /scalping/intelligence/{symbol}/snapshot     — intelligence corrente
- GET  /scalping/intelligence/{symbol}/history      — storico intelligence
- GET  /scalping/session                            — stato sessione
- POST /scalping/session                            — start/stop/pause/resume
- GET  /scalping/position                           — posizione aperta
- GET  /scalping/position/list                      — lista posizioni
- GET  /scalping/performance                        — metriche performance
- GET  /scalping/opportunities                      — opportunità (TASK-810)
- GET  /scalping/opportunities/watchlist            — watchlist simboli
- WS   /ws/scalping                                 — stream eventi real-time
"""

import asyncio  # noqa: F401 — re-exported for test mocks
import json
import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.execution.exchange_models import FeeTier  # noqa: F401 — re-exported for test mocks

from app.scalping.pricing import (
    _get_fee_rate,
    _net_to_gross_pct,
    _sl_gross_fraction,
)

from app.scalping._state import (
    _backtest_results,
    _execution_state,
    _scalping_ws_connections,
)

from app.db.supabase_client import get_supabase  # noqa: F401 — re-exported for test mocks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scalping", tags=["scalping"])

ws_scalping_router = APIRouter(tags=["scalping-ws"])

# ---------------------------------------------------------------------------
# Include REST sub-routers
# ---------------------------------------------------------------------------
from app.scalping.rest.market_data import router as _market_data_router
from app.scalping.rest.backtest import router as _backtest_router
from app.scalping.rest.session import router as _session_router
from app.scalping.rest.position import router as _position_router
from app.scalping.rest.performance import router as _performance_router
from app.scalping.rest.config import router as _config_router
from app.scalping.rest.intel_opportunity import router as _intel_router

router.include_router(_market_data_router)
router.include_router(_backtest_router)
router.include_router(_session_router)
router.include_router(_position_router)
router.include_router(_performance_router)
router.include_router(_config_router)
router.include_router(_intel_router)

# ---------------------------------------------------------------------------
# Backward-compat re-exports (external consumers import these from router.py)
# ---------------------------------------------------------------------------
from app.scalping.broadcast import broadcast_scalping_event, _now  # noqa: F811
from app.scalping.pipeline import _start_ws_broadcast, _stop_ws_broadcast  # noqa: F811
from app.scalping.pricing import (  # noqa: F811
    _get_fee_rate as _get_fee_rate,
    _is_valid_uuid,
    _exit_price_ratio,
    _net_to_gross_pct as _net_to_gross_pct,
    _round_trip_fee_drag_pct,
    _expected_net_pct_at_exit,
    _tp_price_from_entry,
    _sl_gross_fraction as _sl_gross_fraction,
    _sl_price_from_entry,
    _convert_bnb_commission_to_usdc,
    _throttled_warning,
)
from app.scalping.reconciliation import _reconcile_position_with_exchange  # noqa: F811
from app.scalping.db_ops import _save_open_position_to_db, _update_closed_position_in_db  # noqa: F811
from app.scalping.trade_executor import (  # noqa: F811
    _live_close_position,
    _on_order_update,
    _on_uds_reconnect_sync,
    _start_uds_if_needed,
    _handle_bracket_failed,
    _close_position_and_record,
    _check_daily_loss,
    _check_drawdown,
)
from app.scalping.session_lifecycle import (  # noqa: F811
    _refresh_session_balance,
    _sync_session_load_guard,
    _enrich_session_with_threshold,
)
from app.scalping.rest.market_data import _snapshot_to_dict  # noqa: F811


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

# Mounted at /ws in main.py — matches the working /ws proxy rule (ws:// upgrade).
# Full path: /ws/scalping
@ws_scalping_router.websocket("/scalping")
async def scalping_websocket(ws: WebSocket):
    """WebSocket endpoint for real-time scalping events.

    Events emitted:
    - candle:        new candle data
    - trade:         real-time trade (for CVD)
    - signal:        generated signal (BUY/SELL/HOLD)
    - position:      position update (open/close)
    - supervisor:    AI supervisor decision
    - risk_block:    risk manager blocking event
    - intelligence:  intelligence score update
    - opportunity:   new opportunity detected
    """
    await ws.accept()
    _scalping_ws_connections.append(ws)
    logger.info("Scalping WS client connected (%d total)", len(_scalping_ws_connections))

    # ── FIX-2026-06-05: Send initial state to newly connected client ──
    # FIX: also send session state so frontend is in sync after reconnect
    session_data = _execution_state.get("session", {})
    if session_data.get("status") in ("running", "paused"):
        try:
            await ws.send_json({
                "type": "session_restored",
                "payload": session_data.copy(),
                "timestamp": _now(),
            })
        except Exception:
            pass

    pm = _execution_state["position_manager"]
    pos = pm.get_open()
    if pos:
        entry_f = float(pos.entry_price)
        qty_f = float(pos.quantity)
        risk_cfg = _execution_state.get("risk_config", {})
        sl_pct_cfg = float(risk_cfg.get("stop_loss_pct", 0.3))
        tp_pct_cfg = float(risk_cfg.get("take_profit_pct", 0.5))
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        _ef = _get_fee_rate(fee_tier, "taker", 0.001)
        _xf = _get_fee_rate(fee_tier, "taker", 0.001)
        sl_gross_frac = _sl_gross_fraction(sl_pct_cfg, _ef, _xf)
        tp_gross_pct = _net_to_gross_pct(tp_pct_cfg, _ef, _xf) / 100
        sl_price = entry_f * (1 - sl_gross_frac) if pos.side == "BUY" else entry_f * (1 + sl_gross_frac)
        tp_price = entry_f * (1 + tp_gross_pct) if pos.side == "BUY" else entry_f * (1 - tp_gross_pct)
        if pos.sl_price is not None:
            sl_price = float(pos.sl_price)
        if pos.tp_price is not None:
            tp_price = float(pos.tp_price)

        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)
        exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)
        fee_round_trip = (entry_fee_rate + exit_fee_rate) * 100

        sl_pct_net = sl_pct_cfg - fee_round_trip
        tp_pct_net = tp_pct_cfg - fee_round_trip

        try:
            await ws.send_json({
                "type": "position",
                "payload": {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": entry_f,
                    "current_price": entry_f,
                    "entry_time": pos.entry_time.isoformat(),
                    "quantity": qty_f,
                    "pnl": 0.0,
                    "pnl_pct": 0.0,
                    "stop_loss_price": round(sl_price, 2),
                    "take_profit_price": round(tp_price, 2),
                    "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                    "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                    "stop_loss_pct_net": round(sl_pct_net, 2),
                    "take_profit_pct_net": round(tp_pct_net, 2),
                },
                "timestamp": _now(),
            })
            logger.info(f"Initial position state sent to new WS client: {pos.side} {pos.symbol}")
        except Exception:
            pass
    else:
        try:
            await ws.send_json({
                "type": "position",
                "payload": None,
                "timestamp": _now(),
            })
            logger.debug("Sent null position state to new WS client")
        except Exception:
            pass

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong", "timestamp": _now()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if ws in _scalping_ws_connections:
            _scalping_ws_connections.remove(ws)
        logger.info("Scalping WS client disconnected (%d remaining)", len(_scalping_ws_connections))
    except Exception as e:
        if ws in _scalping_ws_connections:
            _scalping_ws_connections.remove(ws)
        logger.error("Scalping WS error: %s", e)
