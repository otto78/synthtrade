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

import asyncio
import json
import logging
import uuid
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.scalping.models.backtest import BacktestConfig, BacktestResult
from app.scalping.models.opportunity import OpportunityCategory, OpportunityUrgency
from app.scalping.opportunity.scheduler import OpportunityScheduler
from app.scalping.backtest.backtest_engine import BacktestEngine
from app.scalping.backtest.historical_loader import HistoricalLoader
from app.scalping.backtest.performance_calculator import PerformanceCalculator
from app.scalping.backtest.report_generator import ReportGenerator
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.engine.position_manager import PositionManager
from app.scalping.models.intelligence import SignalScore, CVDData
from app.db.supabase_client import get_supabase
from app.scalping.data.candle_buffer import CandleBuffer
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.engine.signal_aggregator import SignalAggregator
from app.scalping.engine.regime_detector import RegimeDetector
from app.scalping.engine.strategy_selector import StrategySelector
from app.scalping.models.market import Candle
from app.config import settings
from app.scalping.session_load_guard import SessionLoadGuard
from app.scalping.config_loader import get_scalping_config
from app.core.logging import SessionContextFilter
from app.core.session_log_handler import SessionLogHandler
from app.core.signal_log_writer import (
    log_signal_decision,
    log_block_decision,
    log_hold_decision,
    log_execution_error,
    log_mean_reversion_decision,
    log_rejected_short_unsupported,
)
from app.execution.exchange_models import MarketOrderRequest, OrderSide, SymbolRef, ClosePositionRequest, ExitBracketRequest, FeeTier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scalping", tags=["scalping"])

# Dedicated WebSocket router — mounted at app level (no prefix) in main.py
# so it matches the /ws proxy rule which handles WS upgrade reliably.
ws_scalping_router = APIRouter(tags=["scalping-ws"])

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
    },
    "trade_history": [],        # List[dict] — trade history for performance calc
    "risk_config": {
        "max_daily_loss": 50,
        "max_drawdown": 10,
        "leverage": 10,
        "stop_loss_pct": 0.3,
        "take_profit_pct": 0.5,
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

def _throttled_warning(msg: str, key: str = "") -> None:
    """Emette un warning solo se non è già stato emesso negli ultimi N secondi."""
    import time
    now = time.time()
    throttle_key = key or msg[:80]
    last = _last_warning.get(throttle_key, 0.0)
    if now - last >= _warning_throttle_sec:
        logger.warning(msg)
        _last_warning[throttle_key] = now
    else:
        logger.debug(f"[THROTTLED] {msg}")


def _is_valid_uuid(value: str) -> bool:
    """Return True if value is a valid UUID string."""
    import re
    return bool(re.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        str(value).lower()
    ))


def _net_to_gross_pct(net_pct: float, entry_fee_rate: float, exit_fee_rate: float) -> float:
    """Converte un target NETTO (%) nel movimento di prezzo LORDO (%) necessario
    perché, dopo le due fee (entry + exit), il risultato netto coincida col target.

    net_pct può essere positivo (TP) o negativo (SL) — la formula è la stessa
    perché la fee si applica sempre a sfavore su entrambe le leg.

    Esempi con fee entry=0.00095 taker, exit=0.001 maker:
        _net_to_gross_pct(+0.5,  0.00095, 0.001) ->  +0.6963%  (TP allargato)
        _net_to_gross_pct(-0.3,  0.00095, 0.001) ->  -0.1053%  (SL ristretto)

    NOTA: exit_fee_rate usa "maker" per coerenza con la convenzione già adottata
    in tutto il codebase (_on_order_update, _close_position_and_record, ecc.).
    Lo SL su Binance OCO potrebbe eseguire come taker — non ancora verificato
    sui dati reali. Se si osserva una discrepanza sistematica tra SL netto atteso
    e osservato, rivedere questa assunzione e passare taker per exit_fee_rate sullo SL.
    """
    net = net_pct / 100
    gross = (1 + net) / ((1 - entry_fee_rate) * (1 - exit_fee_rate)) - 1
    return gross * 100


async def _convert_bnb_commission_to_usdc(exchange, bnb_amount: float, context: str = "") -> float:
    """Convert BNB commission to USDC using exchange ticker price.

    Uses a local cache (60s TTL) to minimize API calls.
    Falls back to last known cached price if fetch fails, then to fee-tier estimate.
    Log throttling prevents flood of identical warnings during rate limiting.
    """
    import time
    global _bnb_price_cache
    now = time.time()

    # Try to fetch fresh price (get_ticker_price has its own 15s cache)
    bnb_price = None
    try:
        bnb_price = await exchange.get_ticker_price("BNBUSDC")
        _bnb_price_cache = {"price": bnb_price, "timestamp": now}
    except Exception as e:
        # Use local cache if available (60s TTL)
        if now - _bnb_price_cache["timestamp"] < _bnb_price_cache_ttl and _bnb_price_cache["price"] > 0:
            bnb_price = _bnb_price_cache["price"]
            _throttled_warning(
                f"{context}failed to fetch BNB price: {e} — using cached price ({bnb_price})",
                key=f"bnb_price_fetch_{context}"
            )
        else:
            _throttled_warning(
                f"{context}failed to convert {bnb_amount} BNB to USDC: {e} — using fee-tier estimate",
                key=f"bnb_conv_fail_{context}"
            )

    if bnb_price is not None and bnb_price > 0:
        usdc_value = bnb_amount * bnb_price
        logger.debug(f"{context}converted {bnb_amount} BNB to {usdc_value:.4f} USDC @ {bnb_price}")
        return usdc_value

    # Ultimate fallback: fee-tier estimate
    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    entry_fee_rate = fee_tier.get("taker", 0.001)
    entry_val = float(_execution_state.get("session", {}).get("live_balance", 0))
    return entry_val * entry_fee_rate if entry_val > 0 else 0.0

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
    # Send the current position state so the frontend doesn't show stale data
    # after a WS reconnect. The client receives position_update immediately.
    pm = _execution_state["position_manager"]
    pos = pm.get_open()
    if pos:
        entry_f = float(pos.entry_price)
        qty_f = float(pos.quantity)
        risk_cfg = _execution_state.get("risk_config", {})
        sl_pct_cfg = float(risk_cfg.get("stop_loss_pct", 0.3))
        tp_pct_cfg = float(risk_cfg.get("take_profit_pct", 0.5))
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        _ef = fee_tier.get("taker", 0.001)
        _xf = fee_tier.get("maker", 0.001)
        # TASK-1127: Fees are now positive for base level accounts (converted in adapter)
        # _net_to_gross_pct works with positive fee rates
        # SL target is a LOSS: pass the NEGATIVE net so _net_to_gross_pct returns
        # the (smaller) gross move that nets that loss AFTER fees.
        sl_gross_pct = _net_to_gross_pct(-sl_pct_cfg, _ef, _xf) / 100
        tp_gross_pct = _net_to_gross_pct(tp_pct_cfg, _ef, _xf) / 100
        # BUY: SL below entry (1 + negative), TP above entry (1 + positive) — SELL: reversed
        sl_price = entry_f * (1 + sl_gross_pct) if pos.side == "BUY" else entry_f * (1 - sl_gross_pct)
        tp_price = entry_f * (1 + tp_gross_pct) if pos.side == "BUY" else entry_f * (1 - tp_gross_pct)
        # TASK-1129: usa i veri prezzi TP/SL piazzati su OKX se disponibili
        # (fallback al ricalcolo da percentuali per posizioni pre-fix / restore).
        if pos.sl_price is not None:
            sl_price = float(pos.sl_price)
        if pos.tp_price is not None:
            tp_price = float(pos.tp_price)
        
        # TASK-885: Calcola target netti TP/SL (fee tier round-trip)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
        exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO orders = maker
        fee_round_trip = (entry_fee_rate + exit_fee_rate) * 100  # converti in percentuale
        
        # Calcola percentuali nette (sottrai fee round-trip dai target lordi)
        sl_pct_net = (sl_pct_cfg * 100) - fee_round_trip  # perdita netta è peggiore
        tp_pct_net = (tp_pct_cfg * 100) - fee_round_trip  # guadagno netto è minore
        
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
                    "stop_loss_pct_net": round(sl_pct_net, 2),  # TASK-885
                    "take_profit_pct_net": round(tp_pct_net, 2),  # TASK-885
                },
                "timestamp": _now(),
            })
            logger.info(f"Initial position state sent to new WS client: {pos.side} {pos.symbol}")
        except Exception:
            pass
    else:
        # Send explicit no-position state so frontend clears any stale position card
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
            # Keep connection alive, receive any client messages
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


async def broadcast_scalping_event(event_type: str, payload: Any):
    """Broadcast an event to all connected scalping WebSocket clients."""
    message = {
        "type": event_type,
        "payload": payload,
        "timestamp": _now(),
    }
    dead = []
    for ws in _scalping_ws_connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _scalping_ws_connections.remove(ws)
    # Always store last error in session state for HTTP response fallback
    if event_type == "error":
        session = _execution_state["session"]
        session["last_error"] = {"code": payload.get("code"), "message": payload.get("message"), "timestamp": message["timestamp"]}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                symbol = session.get("symbol", "BTC-EUR")

                # Derive quote asset from symbol (provider-neutral)
                from app.execution.exchange_models import SymbolRef
                try:
                    sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
                    quote = sym_ref.quote
                except Exception:
                    quote = "EUR"

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

async def _live_close_position(exchange, pos, qty: float) -> float:
    """Execute live close on exchange: cancel open orders + market sell (with retry).

    TASK-1107: Provider-neutral implementation.
    Uses ExchangeAdapterProtocol methods only — works for OKX and Binance.

    Returns the actual execution price on success.
    Raises Exception if close fails after all retries.

    Scenarios handled:
    1. Bracket already executed → no base balance → use current ticker price
    2. Balance check fails → fallback to original qty parameter
    3. Balance >= min_sz → use actual balance, round to lot_sz, market close
    """
    from app.execution.exchange_models import ClosePositionRequest, SymbolRef

    # Parse symbol to SymbolRef (provider-neutral)
    sym_str = pos.symbol.upper()
    try:
        sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)
    except Exception:
        sym_ref = SymbolRef.from_compact(sym_str)

    base_asset = sym_ref.base

    # 1. Cancel any open exit orders (bracket TP/SL) before attempting close
    try:
        await exchange.cancel_open_exit_orders(sym_ref)
        logger.info(f"Cancelled open exit orders for {sym_str}")
    except Exception as order_e:
        logger.warning(f"Could not cancel open exit orders (non-blocking): {order_e}")

    # 2. Get actual available balance to determine if bracket already filled
    try:
        holdings = await exchange.get_holdings()
        actual_qty = holdings.get(base_asset, 0.0)
        rules = await exchange.get_symbol_rules(sym_ref)
        min_qty = rules.min_sz

        if actual_qty < min_qty:
            # ── SCENARIO 1: Bracket already executed ──
            # Exchange already sold (TP or SL filled). Only dust remains.
            # Recover fill price from current ticker as best approximation.
            logger.info(
                f"Balance {actual_qty} {base_asset} < minSz {min_qty}. "
                f"Position already closed by exchange bracket."
            )
            try:
                close_price_to_use = await exchange.get_ticker_price(sym_ref.okx)
                if close_price_to_use > 0:
                    logger.info(f"Using current ticker price as fill approximation: {close_price_to_use}")
                    return close_price_to_use
            except Exception as ticker_e:
                logger.warning(f"Ticker fetch failed, falling back to entry price: {ticker_e}")
            return float(pos.entry_price)

        # ── SCENARIO 3: Position still open, balance >= min_sz ──
        qty = actual_qty
        logger.info(f"Using actual balance for {sym_str} close: {qty}")

    except Exception as bal_err:
        # ── SCENARIO 2: Balance check failed → use original qty parameter ──
        logger.warning(f"Balance check failed (fallback to original qty {qty}): {bal_err}")

    # 3. Round qty to lot_sz precision
    try:
        rules = await exchange.get_symbol_rules(sym_ref)
        qty = rules.round_qty(qty)
        if qty <= 0:
            logger.warning(f"Rounded qty=0 for {sym_str}, using original")
            qty = float(pos.quantity)
    except Exception as round_e:
        logger.warning(f"Could not get symbol rules for rounding ({round_e}), using raw qty")

    # 4. Execute Market Close — retry up to 3 times with delay
    close_res = None
    for attempt in range(3):
        try:
            close_req = ClosePositionRequest(
                symbol=sym_ref,
                side=pos.side.lower(),  # side of the POSITION (not the close order)
                quantity=qty,
            )
            close_res = await exchange.close_position(close_req)
            break
        except Exception as retry_e:
            logger.warning(f"Market close attempt {attempt + 1}/3 failed for {sym_str}: {retry_e}")
            if attempt < 2:
                await asyncio.sleep(0.5)

    if close_res is None:
        raise RuntimeError(f"Failed to close live position for {sym_str} after 3 attempts")

    close_price = float(close_res.average_price or pos.entry_price)
    logger.info(f"LIVE Market Close executed @ {close_price} [{settings.EXCHANGE_PROVIDER.upper()}]")
    return close_price


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


async def _on_order_update(event: dict):
    """Handler UDS — chiamato su ogni executionReport FILLED/EXPIRED.

    TASK-826: Implementa la logica di chiusura posizione via User Data Stream.
    Sostituisce il polling OCO su ogni candela (rimosso in TASK-824).

    Gestione ordine eventi Binance:
    - Se arriva FILLED → chiudiamo la posizione (TP o SL)
    - Se arriva EXPIRED → log informativo. L'altro leg (FILLED) arriverà dopo.
      Se la posizione è già chiusa (pos=None), usciamo silenziosamente.
    """
    symbol = event.get("symbol")
    order_id = event.get("order_id")
    # provider-neutral: OKX uses bracket_id/order_list_id, Binance uses order_list_id
    order_list_id = event.get("bracket_id") or event.get("order_list_id")
    leg = event.get("leg")  # "take_profit" | "stop_loss" | "market" | "algo" (OKX)
    status = event.get("status")   # "filled" / "expired"
    fill_price = event.get("fill_price", 0.0)

    pos = _execution_state["position_manager"].get_open()
    # ⚠️ Se la posizione è già chiusa o non è il nostro bracket → exit silenzioso
    if not pos:
        return
    if pos.oco_order_list_id and order_list_id != pos.oco_order_list_id:
        logger.debug(f"[ORDER_STREAM] event bracket_id={order_list_id} != pos.bracket_id={pos.oco_order_list_id} — skip")
        return

    if status == "filled":
        # Determina se è TP o SL:
        # 1. Da campo leg (OKX algo-orders lo fornisce direttamente)
        # 2. Da orderId matching (Binance legacy)
        if leg == "take_profit":
            reason = "take_profit"
        elif leg == "stop_loss":
            reason = "stop_loss"
        elif order_id and pos.tp_order_id and order_id == pos.tp_order_id:
            reason = "take_profit"
        elif order_id and pos.sl_order_id and order_id == pos.sl_order_id:
            reason = "stop_loss"
        else:
            reason = "bracket_filled"

        if fill_price <= 0:
            logger.warning(f"[ORDER_STREAM] FILLED event with fill_price=0 for {symbol} orderId={order_id} — skip close")
            return

        # TASK-878: Calcola PnL con commissioni reali
        entry_f = float(pos.entry_price)
        qty_f = float(pos.quantity)
        gross_pnl = (fill_price - entry_f) * qty_f if pos.side == "BUY" else (entry_f - fill_price) * qty_f
        
        # Commissione di uscita reale dal WebSocket (TASK-876 / TASK-1107)
        exit_commission = event.get("commission", 0.0)
        exit_commission_asset = event.get("commission_asset")
        
        # OKX: fee is already in quote currency (EUR) or may be in native token.
        # Binance: fee may be in BNB. Generic conversion: try get_ticker_price if not quote.
        session_symbol = _execution_state["session"].get("symbol", "")
        from app.execution.exchange_models import SymbolRef
        try:
            sym_ref = SymbolRef.from_okx(session_symbol) if "-" in session_symbol else SymbolRef.from_compact(session_symbol)
            quote_asset = sym_ref.quote
        except Exception:
            quote_asset = "EUR"
        
        if exit_commission_asset and exit_commission_asset != quote_asset and exit_commission > 0:
            try:
                exchange = _execution_state.get("exchange")
                if exchange:
                    # Try to convert commission asset to quote via ticker
                    ticker_sym = f"{exit_commission_asset}/{quote_asset}"  # e.g. OKB/EUR or BNB/USDT
                    asset_price = await exchange.get_ticker_price(ticker_sym)
                    converted = exit_commission * asset_price
                    logger.debug(
                        "Converted commission %s %s to %.4f %s @ %.4f",
                        exit_commission, exit_commission_asset, converted, quote_asset, asset_price,
                    )
                    exit_commission = converted
            except Exception as e:
                logger.warning("Failed to convert commission %s %s to %s: %s",
                               exit_commission, exit_commission_asset, quote_asset, e)
        
        # Commissione di entrata: usa fee tier se non disponibile da WebSocket
        # (Nota: l'ordine market di entrata non passa attraverso UDS, quindi non abbiamo
        # la commissione reale di entrata. Usiamo il fee tier come costo atteso.)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
        entry_commission = entry_f * qty_f * entry_fee_rate
        
        # Totale fee = entrata (attesa) + uscita (reale)
        total_fees = entry_commission + exit_commission
        
        pnl = gross_pnl - total_fees
        pnl_pct = (pnl / (entry_f * qty_f)) * 100 if entry_f > 0 else 0.0
        
        logger.debug(f"[TASK-878] PnL calc: gross={gross_pnl:.4f}, entry_fee={entry_commission:.4f}, exit_fee={exit_commission:.4f}, total_fees={total_fees:.4f}, pnl={pnl:.4f}")

        # Chiudi posizione in memoria
        _execution_state["position_manager"].close_position(Decimal(str(fill_price)))

        # Aggiorna trade history
        trade_record = {
            "symbol": pos.symbol,
            "side": pos.side,
            "entry_price": entry_f,
            "exit_price": fill_price,
            "quantity": qty_f,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal_reason": reason,
        }
        _execution_state["trade_history"].append(trade_record)

        # Aggiorna DB
        await _update_closed_position_in_db(pos, fill_price, pnl, pnl_pct, reason)

        # Refresh live balance
        await _refresh_session_balance()

        # Broadcast UI
        await broadcast_scalping_event("trade_closed", {
            "symbol": pos.symbol,
            "side": pos.side,
            "entry_price": entry_f,
            "exit_price": fill_price,
            "quantity": qty_f,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "signal_reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"\033[92m✅ Trade chiuso da {reason}: {pos.symbol} @ {fill_price} | PnL={pnl:.2f} ({pnl_pct:.2f}%)\033[0m")

    elif status == "expired":
        # ⚠️ Binance NON garantisce l'ordine FILLED/EXPIRED.
        # Se arriva prima EXPIRED, la posizione è ancora aperta — il FILLED arriverà dopo.
        # Se la posizione è già chiusa (pos=None sopra), usciamo silenziosamente.
        logger.info(f"ℹ️ OCO leg EXPIRED (attesa FILLED dell'altro leg): {symbol} orderId={order_id}")


async def _on_uds_reconnect_sync():
    """Chiamato dopo ogni riconnessione UDS (TASK-830).

    Verifica se l'OCO è stato eseguito durante la finestra di disconnessione.
    Se sì, chiude la posizione in memoria, aggiorna DB e broadcast UI.
    """
    pos = _execution_state["position_manager"].get_open()
    if not pos:
        return  # Nessuna posizione aperta, nulla da sincronizzare

    exchange = _execution_state.get("exchange")
    if not exchange:
        return

    try:
        open_orders = await exchange.get_open_orders(pos.symbol)
        if not open_orders:
            # OCO eseguito durante la disconnessione!
            logger.info(f"🔄 UDS riconnesso: OCO già eseguito per {pos.symbol} durante la disconnessione — recupero fill price")

            fill_price: Optional[float] = None

            # Prova prima con orderId specifici se disponibili (più affidabile)
            for order_id in [pos.tp_order_id, pos.sl_order_id]:
                if order_id:
                    fp = await exchange._fetch_fill_price_by_order_id(pos.symbol, order_id)
                    if fp and fp > 0:
                        fill_price = fp
                        break

            # Fallback: cerca negli ordini chiusi recenti
            if not fill_price:
                try:
                    closed = await exchange.client.fetch_closed_orders(
                        await exchange._get_ccxt_symbol(pos.symbol),
                        limit=10
                    )
                    for order in sorted(closed, key=lambda x: x.get("timestamp", 0), reverse=True):
                        if order.get("status") == "closed" and order.get("side", "").upper() == "SELL":
                            fp = float(order.get("price") or order.get("average") or 0)
                            if fp > 0:
                                fill_price = fp
                                break
                except Exception as e:
                    logger.warning(f"UDS reconnect sync: fetch_closed_orders failed: {e}")

            if not fill_price or fill_price <= 0:
                logger.warning(f"UDS reconnect sync: nessun fill price trovato per {pos.symbol} — skip")
                return

            entry_f = float(pos.entry_price)
            qty_f = float(pos.quantity)
            gross_pnl = (fill_price - entry_f) * qty_f if pos.side == "BUY" else (entry_f - fill_price) * qty_f
            
            # TASK-879: Usa commissioni reali/attese invece di hardcode
            # Entry: commissione reale se disponibile da WebSocket (TASK-876), altrimenti fee tier
            if pos.entry_commission is not None and pos.entry_commission > 0:
                entry_commission = float(pos.entry_commission)
                # Converti BNB to USDC se necessario
                if pos.entry_commission_asset == "BNB":
                    entry_commission = await _convert_bnb_commission_to_usdc(
                        exchange, entry_commission, context="UDS sync: "
                    )
            else:
                # Fallback: usa fee tier per entrata (costo atteso)
                fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
                entry_commission = entry_f * qty_f * entry_fee_rate
            
            # Exit: usa fee tier (non abbiamo la commissione reale di uscita in questo scenario di riconnessione)
            fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
            exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO stop/limit orders = maker
            exit_commission = fill_price * qty_f * exit_fee_rate
            
            total_fees = entry_commission + exit_commission
            pnl = gross_pnl - total_fees
            pnl_pct = (pnl / (entry_f * qty_f)) * 100 if entry_f > 0 else 0.0
            reason = "take_profit" if pnl > 0 else "stop_loss"
            
            logger.debug(f"[TASK-879] UDS sync PnL: gross={gross_pnl:.4f}, entry_fee={entry_commission:.4f}, exit_fee={exit_commission:.4f}, total_fees={total_fees:.4f}, pnl={pnl:.4f}")

            _execution_state["position_manager"].close_position(Decimal(str(fill_price)))
            trade_record = {
                "symbol": pos.symbol, "side": pos.side,
                "entry_price": entry_f, "exit_price": fill_price,
                "quantity": qty_f, "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "signal_reason": reason,
            }
            _execution_state["trade_history"].append(trade_record)
            await _update_closed_position_in_db(pos, fill_price, pnl, pnl_pct, reason)
            await _refresh_session_balance()
            await broadcast_scalping_event("trade_closed", {
                **trade_record,
            })
            logger.info(f"✅ UDS reconnect sync: trade chiuso @ {fill_price} | PnL={pnl:.2f}")

    except Exception as e:
        logger.warning(f"UDS reconnect sync error (non-fatal): {e}")


async def _start_uds_if_needed():
    """Avvia order event stream singleton se non già attivo (TASK-827 / TASK-1107).

    TASK-1107: provider-neutral — uses build_order_stream() factory.
    Per OKX: OkxOrderEventStream (orders + algo-orders WS).
    Per Binance: UserDataStreamManager (legacy).

    Deve essere chiamato dopo bracket confermato.
    Passa sia on_order_update che on_reconnect_sync al manager.
    """
    if _execution_state.get("user_data_stream"):
        return  # Già attivo — singleton check

    session = _execution_state["session"]
    # OKX Demo needs order stream even in test mode (bracket fills come via WS)
    # Binance: only in live mode
    provider = settings.EXCHANGE_PROVIDER.lower()
    if provider == "binance" and session.get("mode") != "live":
        return  # Binance UDS solo in live

    try:
        from app.execution.exchange_factory import build_order_stream
        order_stream = build_order_stream()
        if order_stream is None:
            return  # Paper mode, no stream needed
        await order_stream.start(
            on_order_update=_on_order_update,
            on_reconnect_sync=_on_uds_reconnect_sync,
        )
        _execution_state["user_data_stream"] = order_stream
        logger.info("\033[96m📡 ORDER STREAM ATTIVO: avviato post-bracket confermato [%s]\033[0m", provider)
    except Exception as uds_e:
        logger.warning("[ORDER_STREAM] Avvio fallito (non-fatal): %s", uds_e)


async def _handle_bracket_failed(exchange, symbol: str):
    """Gestione Caso B — Exit bracket fallito (TASK-828 / TASK-1107 provider-neutral).

    1. Cancella ordini orfani aperti (provider-neutral: cancel_open_exit_orders).
    2. Market sell con qty reale post-fee da adapter balance.
    3. Broadcast error a UI.
    4. Nessun salvataggio DB (posizione non è mai stata valida).
    """
    # 1. Cancella ordini orfani (provider-neutral)
    try:
        from app.execution.exchange_models import SymbolRef
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        await exchange.cancel_open_exit_orders(sym_ref)
        logger.info(f"[BRACKET_FAILED] Cancelled open exit orders for {symbol}")
    except Exception as e:
        logger.warning(f"[BRACKET_FAILED] cancel_open_exit_orders failed (non-blocking): {e}")

    # 2. Market sell con qty reale post-fee (provider-neutral)
    try:
        # Get holdings directly from adapter (works for OKX and Binance)
        holdings = await exchange.get_holdings()
        from app.execution.exchange_models import SymbolRef
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        base_asset = sym_ref.base
        actual_qty = holdings.get(base_asset, 0.0)
        
        if actual_qty > 0:
            sym_rules = await exchange.get_symbol_rules(sym_ref)
            min_qty = sym_rules.min_sz
            if actual_qty >= min_qty:
                from app.execution.exchange_models import ClosePositionRequest
                close_req = ClosePositionRequest(
                    symbol=sym_ref,
                    side="buy",  # side is position side, close is opposite
                    quantity=actual_qty,
                )
                await exchange.close_position(close_req)
                logger.info(f"[BRACKET_FAILED] Emergency market sell executed: {actual_qty} {base_asset}")
            else:
                logger.warning(f"[BRACKET_FAILED] qty={actual_qty} < minQty={min_qty} for {symbol} — impossible to sell")
        else:
            logger.error(f"[BRACKET_FAILED] Balance={actual_qty} for {base_asset} — no asset to sell")
    except Exception as e:
        logger.error(f"[BRACKET_FAILED] Emergency market sell failed for {symbol}: {e}")

    # 3. Broadcast error a UI
    await broadcast_scalping_event("error", {
        "code": "BRACKET_FAILED",
        "message": f"Exit bracket failed for {symbol}. Trade closed with emergency market sell, no assets locked.",
    })


async def _close_position_and_record(pm, close_price: float, pos, reason: str = "signal"):
    """Helper to close position, deduct fees, calculate PnL and record trade."""
    qty = float(pos.quantity)
    mode = _execution_state["session"].get("mode", "paper")
    exchange = _execution_state.get("exchange")

    # --- LIVE EXECUTION OVERRIDE ---
    if mode == "live" and exchange:
        close_price = await _live_close_position(exchange, pos, qty)
    # -------------------------------

    entry_val = float(pos.entry_price) * qty
    exit_val = close_price * qty
    gross_pnl = (close_price - float(pos.entry_price)) * qty * (1 if pos.side == "BUY" else -1)
    
    # TASK-880: Usa commissioni reali/attese invece di hardcode
    # Entry: commissione reale se disponibile da WebSocket (TASK-876), altrimenti fee tier
    if pos.entry_commission is not None and pos.entry_commission > 0:
        entry_commission = float(pos.entry_commission)
        # Converti BNB to USDC se necessario
        if pos.entry_commission_asset == "BNB" and exchange:
            entry_commission = await _convert_bnb_commission_to_usdc(
                exchange, entry_commission, context="Close position: "
            )
    else:
        # Fallback: usa fee tier per entrata (costo atteso)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
        entry_commission = entry_val * entry_fee_rate
    
    # Exit: usa fee tier (costo atteso, dato che non abbiamo la commissione reale di uscita in questo scenario)
    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    exit_fee_rate = fee_tier.get("taker", 0.001)  # market order per chiusura manuale = taker
    exit_commission = exit_val * exit_fee_rate
    
    total_fees = entry_commission + exit_commission
    pnl = gross_pnl - total_fees
    pnl_pct = (pnl / entry_val) * 100
    
    logger.debug(f"[TASK-880] Close position PnL: gross={gross_pnl:.4f}, entry_fee={entry_commission:.4f}, exit_fee={exit_commission:.4f}, total_fees={total_fees:.4f}, pnl={pnl:.4f}")
    pm.close_position(Decimal(str(close_price)))
    now_ts = datetime.now(timezone.utc)
    trade_record = {
        "symbol": pos.symbol,
        "side": pos.side,
        "entry_price": float(pos.entry_price),
        "exit_price": close_price,
        "quantity": qty,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "timestamp": now_ts.isoformat(),
        "signal_reason": reason,
    }
    _execution_state["trade_history"].append(trade_record)

    # Refresh live balance after trade close
    await _refresh_session_balance()
    
    if mode == "paper":
        _execution_state["session"]["paper_balance"] += (entry_val + pnl)
        await broadcast_scalping_event("session_restored", _execution_state["session"].copy())

    # Update DB: change status from 'open' to 'closed' with exit data
    await _update_closed_position_in_db(pos, close_price, pnl, pnl_pct, reason)

    await broadcast_scalping_event("trade_closed", trade_record)
    logger.info(f"Position closed ({reason}): {pos.side} {pos.symbol} PnL: {pnl:.2f} ({pnl_pct:.2f}%)")

def _check_daily_loss() -> bool:
    """Return True if max daily loss is exceeded."""
    risk_cfg = _execution_state.get("risk_config", {})
    max_loss = float(risk_cfg.get("max_daily_loss", 50.0))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_pnl = sum(t.get("pnl") or 0.0 for t in _execution_state["trade_history"] if t["timestamp"].startswith(now_str))
    return total_pnl <= -max_loss


def _check_drawdown() -> bool:
    """Return True if max drawdown from peak equity is exceeded."""
    risk_cfg = _execution_state.get("risk_config", {})
    max_dd_pct = float(risk_cfg.get("max_drawdown", 10.0))
    trades = [t for t in _execution_state["trade_history"] if t.get("exit_price") is not None]
    if not trades:
        return False
    base = float(_execution_state["session"].get("paper_balance") or
                 _execution_state["session"].get("live_balance") or 10000.0)
    equity = base
    peak = base
    for t in trades:
        equity += (t.get("pnl") or 0.0)
        if equity > peak:
            peak = equity
    if peak <= 0:
        return False
    dd_pct = (peak - equity) / peak * 100
    return dd_pct >= max_dd_pct

async def _start_ws_broadcast(symbol: str, restore_mode: bool = False):
    """Create WS client, connect to exchange, and broadcast candle/trade events
    to all connected scalping WS clients.
    
    Also feeds the CandleBuffer and ExecutionLoop pipelines for signal generation.
    
    IMPORTANT: Warmup the candle buffer with historical data BEFORE starting the WS client
    to avoid handshake timeouts (the WS will timeout if the event loop is busy loading data).
    
    Args:
        symbol: Trading symbol (lowercase, e.g. "bnbusdc")
        restore_mode: If True, this is a session restore at startup — skips operations
                      that are only valid for a fresh session start (e.g. DB insert).
    """
    session = _execution_state["session"]
    logger.info(
        f">>> _start_ws_broadcast() ENTERED for {symbol} | "
        f"session_status={session['status']} mode={session['mode']} "
        f"restore_mode={restore_mode}"
    )

    is_testnet = session.get("mode") != "live"
    guard = _execution_state.get("session_load_guard")

    # Create pipeline components FIRST (before WS client)
    candle_buffer = CandleBuffer()
    signal_engine = _execution_state.get("signal_engine")
    if not signal_engine:
        signal_engine = SignalScoreEngine.get_or_create(symbol=symbol)
        _execution_state["signal_engine"] = signal_engine

    # Wire CVD calculator: accumulates real-time trade pressure from Binance WS
    # and feeds it into the signal engine so cvd_trend is valorized.
    from app.scalping.intelligence.collectors.cvd_calculator import CVDCalculator
    cvd_calculator = CVDCalculator()
    if hasattr(signal_engine, '_set_cvd_calculator'):
        signal_engine._set_cvd_calculator(cvd_calculator)
    _execution_state["cvd_calculator"] = cvd_calculator

    _session_mode = _execution_state["session"].get("mode", "paper")
    execution_loop = ExecutionLoop(
        symbol=symbol,
        candle_buffer=candle_buffer,
        signal_engine=signal_engine,
        signal_aggregator=SignalAggregator(),
        regime_detector=RegimeDetector(),
        strategy_selector=StrategySelector(),
        position_manager=_execution_state["position_manager"],
    )
    # paper_mode controls whether intelligence gating is bypassed for low-score markets.
    # Must be False in live mode so the full intelligence + technical filter applies.
    execution_loop.paper_mode = (_session_mode != "live")
    _execution_state["loop"] = execution_loop
    logger.info(f"ExecutionLoop paper_mode={execution_loop.paper_mode} for {symbol} (mode={_session_mode})")

    # Warm up the candle buffer with historical candles BEFORE starting WS client.
    # This prevents: (1) WS handshake timeout from event loop being busy, and
    # (2) the buffer being empty when the first WS closed candle arrives.
    try:
        from app.scalping.backtest.historical_loader import HistoricalLoader
        loader = HistoricalLoader()
        logger.info(f"Pre-loading past 100 1m candles for {symbol.upper()} to warm up buffer...")
        past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
        if past_candles:
            loaded_count = 0
            for c in past_candles:
                if hasattr(c, "timestamp") and hasattr(c, "open"):
                    candle_buffer.add(c)
                    loaded_count += 1
            # Non broadcastare le candele storiche via WS - il frontend usa HTTP /candles/{symbol}
            logger.info(
                f"Successfully loaded {loaded_count} historical candles for {symbol} "
                f"(available via HTTP /candles/{symbol}). "
                f"Buffer size: {len(candle_buffer)}, ready: {candle_buffer.is_ready(50)}"
            )
            
            # ── FIX: Allinea buffer reference (CATEGORIA 6) ──────────────────
            # Il buffer mismatch era causato da un problema di referenziamento:
            # candle_buffer veniva passato all'ExecutionLoop, ma internamente
            # ExecutionLoop copiava il riferimento e non lo manteneva allineato.
            # Forziamo l'allineamento diretto del riferimento.
            if len(execution_loop._candle_buffer) < 50:
                logger.info(
                    f"Buffer sync: aligning execution_loop buffer with candle_buffer "
                    f"(candle_buffer len={len(candle_buffer)}, "
                    f"execution_loop buffer len={len(execution_loop._candle_buffer)}). "
                    f"Setting direct reference..."
                )
                execution_loop._candle_buffer = candle_buffer
                logger.info(
                    f"Buffer sync complete. "
                    f"Buffer now: {len(execution_loop._candle_buffer)}, "
                    f"ready: {execution_loop._candle_buffer.is_ready(50)}"
                )

            if guard:
                guard.complete_phase("buffer_phase")

            # ── FORCE FIRST PIPELINE PROCESS ──────────────────────────────────
            # Dopo il warmup, il buffer ha 100 candele ma process_candle() non viene
            # chiamato finché non arriva una candela chiusa da Binance WS. In caso di
            # riconnessione post-reload, la WS Binance può impiegare minuti a
            # riconnettersi, lasciando il regime su "unknown" (confidence 0.00) e
            # il supervisor in loop infinito a chiamare l'AI.
            # 
            # Forziamo process_candle() sull'ultima candela del warmup per calcolare
            # subito il regime e attivare la strategia corretta.
            if past_candles and loaded_count >= 50:
                last = past_candles[-1]
                forced_candle = Candle(
                    symbol=symbol.upper(),
                    open=Decimal(str(last.open)),
                    high=Decimal(str(last.high)),
                    low=Decimal(str(last.low)),
                    close=Decimal(str(last.close)),
                    volume=Decimal(str(last.volume)),
                    timestamp=getattr(last, 'timestamp', datetime.now(timezone.utc)),
                    closed=True,
                )
                try:
                    _forced_decision = await execution_loop.process_candle(forced_candle)
                    if _forced_decision:
                        _d = _forced_decision
                        logger.info(
                            f">>> FORCED FIRST PIPELINE: regime={execution_loop._current_regime.regime if execution_loop._current_regime else 'N/A'} "
                            f"strategy={execution_loop._strategy.name if execution_loop._strategy else 'N/A'} "
                            f"decision=execute={_d.execute} confidence={_d.confidence:.2f} reason='{_d.reason}' type={_d.signal_type}"
                        )
                except Exception as forced_err:
                    logger.warning(f"First forced process_candle failed (non-fatal): {forced_err}")
            
        else:
            logger.warning(f"No historical candles returned for {symbol}, buffer will warm up live.")
    except Exception as warmup_err:
        logger.error(f"Could not warm up candle buffer with historical data: {warmup_err}", exc_info=True)

    # TASK-1107: provider-neutral WS client via factory (OKX or Binance)
    from app.execution.exchange_factory import build_ws_client
    client = build_ws_client(symbols=[symbol])
    _execution_state["ws_client"] = client
    await client.start()

    if guard:
        guard.complete_phase("pipeline_phase")


    # Pull events from WS client queues and broadcast to scalping WS clients
    async def _candle_processor():
        """Consume candle_queue and broadcast + feed execution loop.
        
        SAFETY: On first execution, verify the buffer has warmup data.
        If warmup failed (e.g. REST timeout), force-reload candles here
        so the buffer is ready for signal generation.
        """
        nonlocal client
        _first_candle = True
        _last_event_time = datetime.now(timezone.utc)
        
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            try:
                event = await asyncio.wait_for(client.candle_queue.get(), timeout=1.0)
                _last_event_time = datetime.now(timezone.utc)
            except asyncio.TimeoutError:
                if _execution_state["session"]["status"] == "idle":
                    break
                
                # ── FIX-2026-06-05: Watchdog — check if data is stale ──
                # If no candle received for > 3 minutes, the WS may be stuck.
                # Force-reload historical candles via REST to keep the pipeline alive,
                # and restart the WS client connection.
                stale_seconds = (datetime.now(timezone.utc) - _last_event_time).total_seconds()

                # LOG every 30s when no data received (reduced level: candles arrive via REST poller
                # every ~55s, so this is expected and not an error)
                if 30 <= stale_seconds < 35:
                    logger.debug(
                        f"No WS candle data for {stale_seconds:.0f}s for {symbol} — "
                        f"candles arriving via REST poller every ~55s"
                    )
                
                if stale_seconds > 180:  # 3 minutes
                    logger.warning(
                        f">>> CANDLE_PROC WATCHDOG: No data for {stale_seconds:.0f}s. "
                        f"Force-reloading candles via REST API..."
                    )
                    _last_event_time = datetime.now(timezone.utc)  # reset to avoid spamming
                    
                    # Load fresh candles via REST API directly into the buffer
                    try:
                        from app.scalping.backtest.historical_loader import HistoricalLoader
                        loader = HistoricalLoader()
                        fresh_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
                        if fresh_candles:
                            loaded = 0
                            for c in fresh_candles:
                                if hasattr(c, "timestamp") and hasattr(c, "open"):
                                    execution_loop._candle_buffer.add(c)
                                    loaded += 1
                                await broadcast_scalping_event("candle", {
                                    "symbol": symbol,
                                    "open": float(c.open),
                                    "high": float(c.high),
                                    "low": float(c.low),
                                    "close": float(c.close),
                                    "volume": float(c.volume),
                                    "timestamp": c.timestamp.isoformat() if hasattr(c.timestamp, 'isoformat') else str(c.timestamp),
                                })
                            logger.info(f">>> CANDLE_PROC WATCHDOG: Loaded {loaded} fresh candles via REST")
                    except Exception as rest_e:
                        logger.error(f">>> CANDLE_PROC WATCHDOG: REST reload failed: {rest_e}")
                    
                    # TASK-907: Full WS and tasks restart
                    try:
                        if not client._stop_event.is_set():
                            logger.info(">>> CANDLE_PROC WATCHDOG: Triggering full WS restart...")
                            
                            async def _full_restart():
                                try:
                                    # Stop Vecchio Client (chiude le code)
                                    logger.info(">>> RESTART_WS: Stopping old client...")
                                    await client.stop()
                                    
                                    # Ferma Supervisor se presente
                                    old_supervisor = _execution_state.get("supervisor_scheduler")
                                    if old_supervisor:
                                        old_supervisor.stop()
                                    
                                    # Cancella vecchi task (incluso me stesso alla fine)
                                    logger.info(">>> RESTART_WS: Cancelling old tasks...")
                                    for t in _execution_state.get("ws_tasks", []):
                                        if t != asyncio.current_task():
                                            t.cancel()
                                    
                                    await asyncio.sleep(2)
                                    
                                    if _execution_state["session"]["status"] == "running":
                                        logger.info(">>> RESTART_WS: Calling _start_ws_broadcast(restore_mode=True)...")
                                        await _start_ws_broadcast(symbol, restore_mode=True)
                                        logger.info(">>> RESTART_WS: Full restart completed!")
                                except Exception as inner_e:
                                    logger.error(f">>> RESTART_WS: Failed: {inner_e}")
                            
                            asyncio.create_task(_full_restart(), name="ws-full-restart-watchdog")
                            
                            # Esci da questo `_candle_processor` così muore pulito, il nuovo prenderà il suo posto.
                            break
                    except Exception as ws_e:
                        logger.error(f">>> CANDLE_PROC WATCHDOG: WS restart failed: {ws_e}")

                    # ── WAKEUP BALANCE CHECK ────────────────────────────────────
                    # When the PC resumes from standby, the WS watchdog fires after
                    # 3 minutes of stale data. This is the ideal moment to refresh
                    # the live balance and detect if Spot funds moved to Earn during
                    # the inactive period. If spot balance is zero, auto-pause session.
                    if _execution_state["session"].get("mode") == "live":
                        try:
                            logger.info(">>> WAKEUP: Refreshing balance after standby...")
                            await _refresh_session_balance()
                            bal = _execution_state["session"].get("live_balance", 0)
                            trade_val = float(_execution_state["session"].get("trade_value", 10.0))
                            if bal is None or bal <= 0 or bal < trade_val:
                                logger.warning(
                                    f"\033[91m⚠️ WAKEUP: Spot balance={bal} < trade_value={trade_val}. "
                                    f"All funds may be in Earn. Pausing session.\033[0m"
                                )
                                _execution_state["session"]["status"] = "paused"
                                await broadcast_scalping_event("session_restored", {
                                    **_execution_state["session"].copy(),
                                    "status": "paused",
                                    "pause_reason": "SPOT_BALANCE_ZERO",
                                    "pause_message": "I tuoi fondi sono in Simple Earn. Spostali su Spot e fai Resume.",
                                })
                            else:
                                logger.info(f">>> WAKEUP: Spot balance OK: {bal}")
                        except Exception as bal_e:
                            logger.warning(f">>> WAKEUP: Balance refresh failed (non-fatal): {bal_e}")
                
                continue

            # SAFETY: On first candle event, check if buffer was properly warmed up.
            # If not (warmup may have failed or buffer instances diverged), 
            # force-load candles directly into the ExecutionLoop's buffer.
            if _first_candle:
                _first_candle = False
                if len(execution_loop._candle_buffer) < 50:
                    logger.warning(
                        f">>> CANDLE_PROC SAFETY: buffer has only {len(execution_loop._candle_buffer)} candles. "
                        f"Force-loading warmup data into ExecutionLoop buffer (id={id(execution_loop._candle_buffer)})..."
                    )
                    try:
                        from app.scalping.backtest.historical_loader import HistoricalLoader
                        loader = HistoricalLoader()
                        past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
                        if past_candles:
                            for c in past_candles:
                                if hasattr(c, "timestamp") and hasattr(c, "open"):
                                    execution_loop._candle_buffer.add(c)
                            logger.info(f">>> CANDLE_PROC SAFETY: Force-loaded {len(past_candles)} candles. Buffer now: {len(execution_loop._candle_buffer)}")
                    except Exception as reload_err:
                        logger.error(f">>> CANDLE_PROC SAFETY: Force-load failed: {reload_err}")

            # Broadcast to frontend WS clients
            await broadcast_scalping_event("candle", {
                "symbol": event.symbol,
                "open": event.open,
                "high": event.high,
                "low": event.low,
                "close": event.close,
                "volume": event.volume,
                "timestamp": datetime.fromtimestamp(event.open_time / 1000, tz=timezone.utc).isoformat(),
            })

            # TRACE: log every event to understand flow (debug-only, too noisy for info)
            buf_size = len(execution_loop._candle_buffer) if execution_loop._candle_buffer else -1
            logger.debug(f">>> CANDLE EVENT: {event.symbol} is_closed={event.is_closed} close={event.close} buffer={buf_size} session_status={_execution_state['session']['status']}")

            # Feed into execution loop for signal generation (only closed candles)
            if event.is_closed:
                guard = _execution_state.get("session_load_guard")
                if guard and not guard.is_ready():
                    guard.record_trade_attempt(event.symbol, "candle_processor")
                    _sync_session_load_guard()
                    continue
                if _execution_state["session"]["status"] != "running":
                    logger.info(f">>> SKIP: session not running (status={_execution_state['session']['status']})")
                    continue
                
                candle = Candle(
                    symbol=event.symbol.upper(),
                    open=Decimal(str(event.open)),
                    high=Decimal(str(event.high)),
                    low=Decimal(str(event.low)),
                    close=Decimal(str(event.close)),
                    volume=Decimal(str(event.volume)),
                    timestamp=datetime.fromtimestamp(event.open_time / 1000, tz=timezone.utc),
                    closed=True,
                )
                logger.info(f">>> PROCESSING closed candle for {event.symbol} @ {candle.close}")
                try:
                    decision = await execution_loop.process_candle(candle)
                    # Sync actual running strategy to session for frontend display
                    if execution_loop._strategy and execution_loop._strategy.name:
                        actual_strategy = execution_loop._strategy.name
                        if session.get("strategy") != actual_strategy:
                            session["strategy"] = actual_strategy
                            logger.info(f"Session strategy synced to actual: {actual_strategy}")
                            await broadcast_scalping_event("session_restored", session.copy())
                    if decision and decision.execute:
                        pm = _execution_state["position_manager"]
                        
                        # TASK-894/895: initialize signal_log_id before conditional branching
                        # to ensure it's always bound when used for DB persistence below
                        _signal_log_id = None
                        
                        # ── FIX: If already in position, only allow CLOSE signals ──
                        # This prevents BUY/SELL spam while still allowing supervisor
                        # to update parameters and strategies in background.
                        # Non trade signals are kept for supervisor analysis.
                        if pm.has_open() and decision.signal_type != "CLOSE":
                            logger.debug(
                                f">>> SKIP broadcasting signal for {event.symbol}: "
                                f"has_open=True, signal_type={decision.signal_type} "
                                f"(keeping for supervisor background analysis)"
                            )
                        else:
                            logger.info(f">>> DECISION APPROVED -> {decision.reason} | confidence={decision.confidence}")
                            # TASK-894/895: log decisione execute su session_signal_log, cattura ID per collegamento
                            # TASK-912: usa il flag is_mean_reversion_override per decidere quale logging function chiamare
                            _ms = execution_loop._last_market_score
                            if getattr(decision, 'is_mean_reversion_override', False):
                                # TASK-912: Log mean-reversion override correttamente
                                _signal_log_id = await asyncio.to_thread(
                                    log_mean_reversion_decision,
                                    session_id=session.get("db_session_id") or session.get("session_id") or "",
                                    symbol=event.symbol.upper(),
                                    override_reason=decision.reason or "",
                                    regime=execution_loop._current_regime.regime if execution_loop._current_regime else "unknown",
                                    strategy_type=execution_loop._strategy.name if execution_loop._strategy else "unknown",
                                    tech_signal=decision.signal_type,
                                    tech_confidence=round(abs(decision.confidence), 3),
                                    intel_score=float(_ms.total) if _ms else None,
                                    intel_bias=_ms.bias if _ms else None,
                                    trend_direction=_ms.trend_direction if _ms else None,
                                    trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                                )
                            else:
                                # Logging normale per execute
                                _signal_log_id = await asyncio.to_thread(
                                    log_signal_decision,
                                    session_id=session.get("db_session_id") or session.get("session_id") or "",
                                    symbol=event.symbol.upper(),
                                    decision_type="execute",
                                    decision_reason=decision.reason,
                                    regime=execution_loop._current_regime.regime if execution_loop._current_regime else "unknown",
                                    strategy_type=execution_loop._strategy.name if execution_loop._strategy else "unknown",
                                    tech_signal=decision.signal_type,
                                    tech_confidence=round(abs(decision.confidence), 3),
                                    intel_score=float(_ms.total) if _ms else None,
                                    intel_bias=_ms.bias if _ms else None,
                                    trend_direction=_ms.trend_direction if _ms else None,
                                    trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                                )
                            # A signal was generated — broadcast it
                            await broadcast_scalping_event("signal", {
                                "symbol": event.symbol.upper(),
                                "type": decision.signal_type,
                                "price": float(candle.close),
                                "confidence": abs(decision.confidence),
                                "reason": decision.reason,
                            })

                        # Simulate trade execution
                        side = decision.signal_type
                        logger.info(f">>> TRADE: side={side} has_open={pm.has_open()} daily_loss={_check_daily_loss()}")
                        
                        guard = _execution_state.get("session_load_guard")
                        if guard and not guard.is_ready():
                            guard.record_trade_attempt(event.symbol.upper(), "live_trade_gate")
                            _sync_session_load_guard()
                            await broadcast_scalping_event("warn", {
                                "code": "SESSION_NOT_READY",
                                "reason": guard.monitor_data.get("error", "loading"),
                            })
                            continue

                        if not pm.has_open():
                            if side == "SELL":
                                logger.info("Short selling non implementato — segnale SELL ignorato (feature futura)")
                                # TASK-913: Logga il rifiuto short con decision_type corretto
                                _ms = execution_loop._last_market_score
                                await asyncio.to_thread(
                                    log_rejected_short_unsupported,
                                    session_id=session.get("db_session_id") or session.get("session_id") or "",
                                    symbol=event.symbol.upper(),
                                    regime=execution_loop._current_regime.regime if execution_loop._current_regime else "unknown",
                                    strategy_type=execution_loop._strategy.name if execution_loop._strategy else "unknown",
                                    tech_signal=decision.signal_type,
                                    tech_confidence=round(abs(decision.confidence), 3),
                                    intel_score=float(_ms.total) if _ms else None,
                                    intel_bias=_ms.bias if _ms else None,
                                    trend_direction=_ms.trend_direction if _ms else None,
                                    trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                                )
                                continue

                            # Only BUY signals reach this point (CLOSE/NONE already filtered)
                            if side != "BUY":
                                logger.debug(f"Skipping non-BUY signal: {side}")
                                continue

                            if _check_daily_loss():
                                logger.warning("Max daily loss exceeded. Blocking new real trade.")
                                continue

                            if _check_drawdown():
                                risk_cfg = _execution_state.get("risk_config", {})
                                logger.warning(f"Max drawdown {risk_cfg.get('max_drawdown', 10)}% exceeded. Blocking new real trade.")
                                await broadcast_scalping_event("error", {"code": "MAX_DRAWDOWN", "message": f"Max drawdown exceeded. Trading bloccato."})
                                continue

                            # --- COMPILE SUPERVISOR CONTEXT ---
                            supervisor_context = {}
                            try:
                                exchange = _execution_state.get("exchange")
                                if exchange:
                                    macro = await exchange.get_btc_macro_context()
                                    supervisor_context.update(macro)
                                
                                supervisor_context["candlestick_pattern"] = getattr(decision, "ta_patterns", None)
                                supervisor_context["volume_anomaly"] = getattr(decision, "vol_anomaly", False)
                                
                                supervisor_context["regime_classified"] = getattr(decision, "regime", None)
                                supervisor_context["strategy_rejection_reason"] = getattr(decision, "reason", None)
                                supervisor_context["signal_price"] = float(candle.close)
                            except Exception as ctx_e:
                                logger.warning(f"Failed to compile supervisor context: {ctx_e}")
                            # ----------------------------------

                            # Mode and trade values
                            _mode = _execution_state["session"].get("mode", "paper")
                            _trade_val = float(_execution_state["session"].get("trade_value", 10.0))
                            
                            if _mode == "live":
                                exchange = _execution_state.get("exchange")
                                if not exchange:
                                    logger.error("Live mode requested but exchange is not initialized!")
                                    continue
                                    
                                try:
                                    # 1. Get exact symbol filters for precision
                                    filters = await exchange.get_symbol_filters(event.symbol.upper())
                                    
                                    # 2. Compute exact quantity
                                    min_notional = float(filters.get("minNotional", 5.0))
                                    if _trade_val < min_notional:
                                        logger.warning(f"Trade value {_trade_val} below minNotional {min_notional}, adjusting")
                                        _trade_val = min_notional
                                    _qty_raw = _trade_val / float(event.close)
                                    step_size = float(filters["stepSize"])
                                    _qty_precise = round(math.floor(_qty_raw / step_size) * step_size, 8)
                                    
                                    # 3. Check real free balance in quote asset BEFORE placing order
                                    try:
                                        ccxt_bal = await exchange.client.fetch_balance()
                                        bal_total = ccxt_bal.get("total", {})
                                        bal_free = ccxt_bal.get("free", {})
                                        quote_asset = filters.get("quoteAsset", "USDT")
                                        
                                        free_quote = float(bal_free.get(quote_asset, 0.0))
                                        total_quote = float(bal_total.get(quote_asset, 0.0))
                                        
                                        logger.info(
                                            f"LIVE BALANCE: {quote_asset} free={free_quote} total={total_quote} "
                                            f"trade_cost={_qty_precise * float(event.close):.2f}"
                                        )
                                        
                                        if free_quote < _qty_precise * float(event.close):
                                            logger.error(
                                                f"Insufficient {quote_asset} in SPOT wallet. "
                                                f"free={free_quote} (available for trading) vs total={total_quote} (includes Earn/Funding). "
                                                f"Please move funds from Earn to Spot wallet."
                                            )
                                            await broadcast_scalping_event("error", {
                                                "code": "INSUFFICIENT_SPOT_BALANCE",
                                                "message": f"Insufficient {quote_asset} in Spot wallet (free={free_quote:.2f}, total={total_quote:.2f}). Move funds from Earn to Spot.",
                                            })
                                            continue
                                    except Exception as bal_e:
                                        logger.warning(f"Balance check failed (non-blocking): {bal_e}")
                                    
                                    logger.info(f"LIVE TRADE CALC: symbol={event.symbol}, trade_value={_trade_val}, price={event.close}, qty_raw={_qty_raw}, step_size={step_size}, qty_precise={_qty_precise}, min_qty={filters['minQty']}")
                                    
                                    if _qty_precise < float(filters["minQty"]):
                                        logger.error(f"Quantity too small: {_qty_precise} < {filters['minQty']} - TRADE BLOCKED")
                                        await broadcast_scalping_event("error", {
                                            "code": "QTY_TOO_SMALL",
                                            "message": f"Trade quantity {_qty_precise} below minimum {filters['minQty']}",
                                        })
                                        continue
                                        
                                    # 3. Execute Market Buy
                                    from app.execution.exchange_models import MarketOrderRequest, SymbolRef

                                    sym_str = event.symbol.upper()
                                    sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)

                                    # side is "BUY" (validated above)
                                    # FIX-2026-07-10: Use quote_amount (EUR) instead of quantity (OKB)
                                    # for BUY market orders so OKX uses tgtCcy=quote_ccy and calculates
                                    # the base quantity respecting its own minSz constraints.
                                    # This fixes sCode=51020 "Your order should meet or exceed the minimum order amount."
                                    market_request = MarketOrderRequest(
                                        symbol=sym_ref,
                                        side="buy",  # 'buy' o 'sell'
                                        quote_amount=_trade_val,  # OKX calcola la quantità base da sola
                                    )
                                    market_res = await exchange.place_market_order(market_request)

                                    exec_price = float(market_res.average_price or event.close)
                                    # TASK-1128 FIX: The market order uses quote_amount (EUR) so the REST
                                    # fallback returns sz=20 (EUR input) and accFillSz=0 (not filled yet).
                                    # Using market_res.quantity here gives 20 EUR misread as OKB.
                                    # Correct fallback: use _qty_precise (pre-calculated base qty).
                                    exec_qty = float(market_res.filled) if market_res.filled and float(market_res.filled) > 0 else _qty_precise

                                    # TASK-886: commissione reale dell'entry, dalla risposta dell'ordine market
                                    entry_commission_real = float(market_res.commission or 0.0)
                                    entry_commission_asset_real = market_res.commission_asset

                                    # 4. Calculate Risk SL/TP with proper price precision
                                    # I valori configurati (stop_loss_pct, take_profit_pct) rappresentano
                                    # il risultato NETTO atteso dopo fee. Convertiamo nel movimento di
                                    # prezzo LORDO necessario tramite _net_to_gross_pct.
                                    risk_cfg = _execution_state.get("risk_config", {})
                                    sl_pct_net_cfg = float(risk_cfg.get("stop_loss_pct", 0.3))
                                    tp_pct_net_cfg = float(risk_cfg.get("take_profit_pct", 0.5))
                                    price_prec = int(filters.get("pricePrecision", 2))

                                    fee_tier_pricing = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                                    # TASK-1127: Fees are now positive for base level accounts (converted in adapter)
                                    entry_fee_pricing = fee_tier_pricing.get("taker", 0.001)
                                    exit_fee_pricing = fee_tier_pricing.get("maker", 0.001)

                                    # TASK-1127: SL/TP gross price calculation.
                                    # _net_to_gross_pct returns a positive magnitude for both TP and SL.
                                    # SL target is a LOSS: pass the NEGATIVE net so _net_to_gross_pct
                                    # returns the (smaller) gross move that nets that loss AFTER fees.
                                    sl_gross_pct = _net_to_gross_pct(-sl_pct_net_cfg, entry_fee_pricing, exit_fee_pricing) / 100
                                    tp_gross_pct = _net_to_gross_pct(tp_pct_net_cfg, entry_fee_pricing, exit_fee_pricing) / 100

                                    # BUY:  SL = below entry (exec * (1 + negative)), TP = above entry (exec * (1 + tp_pct))
                                    # SELL: SL = above entry (exec * (1 - negative)), TP = below entry (exec * (1 - tp_pct))
                                    sl_price = round(exec_price * (1 + sl_gross_pct), price_prec) if side == "BUY" else round(exec_price * (1 - sl_gross_pct), price_prec)
                                    tp_price = round(exec_price * (1 + tp_gross_pct), price_prec) if side == "BUY" else round(exec_price * (1 - tp_gross_pct), price_prec)

                                    logger.info(
                                         f"[NET_PRICING] provider={settings.EXCHANGE_PROVIDER} symbol={event.symbol} maker={exit_fee_pricing} taker={entry_fee_pricing} certified={_execution_state.get('fee_tier_certified', False)} | "
                                        f"Target netti: TP={tp_pct_net_cfg}% SL={sl_pct_net_cfg}% | "
                                        f"Lordi al prezzo: TP=+{tp_gross_pct*100:.4f}% SL=-{sl_gross_pct*100:.4f}% | "
                                        f"sl_price={sl_price} tp_price={tp_price} | "
                                        f"fee entry={entry_fee_pricing} exit={exit_fee_pricing}"
                                    )

                                    # 5. Place exit bracket (TASK-1107: provider-neutral)
                                    bracket_res = None
                                    bracket_failed = False
                                    try:
                                        from app.execution.exchange_models import ExitBracketRequest, SymbolRef, FeeTier
                                        
                                        # Parse symbol to SymbolRef
                                        sym_str = event.symbol.upper()
                                        sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)
                                        
                                        # Build fee tier object for bracket request
                                        fee_tier_obj = FeeTier(
                                            maker=exit_fee_pricing,
                                            taker=entry_fee_pricing,
                                            certified=_execution_state.get("fee_tier_certified", False),
                                            source="execution_state",
                                        )
                                        
                                        # TASK-1128: Calculate exact bracket quantity to avoid 51008.
                                        # OKX deducts the taker fee in the base asset before the OCO goes live.
                                        # Strategy: read the ACTUAL available balance from OKX (most reliable),
                                        # fall back to estimated qty if the REST call fails.
                                        bracket_qty = exec_qty  # safe initial fallback
                                        if side == "BUY":
                                            try:
                                                # Ask OKX directly what balance is available right now
                                                actual_bal = await exchange._balance_from_rest(sym_ref.base)
                                                if actual_bal > 0:
                                                    bracket_qty = actual_bal
                                                    logger.info(f"[BRACKET_QTY] actual_balance={actual_bal:.6f} {sym_ref.base} (from REST) — using as bracket qty")
                                                else:
                                                    # REST returned 0 (unlikely) — estimate fee
                                                    estimated_fee = exec_qty * entry_fee_pricing
                                                    bracket_qty = exec_qty - estimated_fee
                                                    logger.warning(f"[BRACKET_QTY] balance=0 from REST, using estimate: exec_qty={exec_qty:.6f} - fee={estimated_fee:.6f} = {bracket_qty:.6f}")
                                            except Exception as _bal_e:
                                                estimated_fee = exec_qty * entry_fee_pricing
                                                bracket_qty = exec_qty - estimated_fee
                                                logger.warning(f"[BRACKET_QTY] balance REST failed ({_bal_e}), using estimate: {bracket_qty:.6f}")
                                            bracket_qty = round(bracket_qty, 8)

                                                
                                        bracket_req = ExitBracketRequest(
                                            symbol=sym_ref,
                                            side="sell" if side == "BUY" else "buy",
                                            quantity=bracket_qty,
                                            tp_price=tp_price,
                                            sl_price=sl_price,
                                            entry_order_id=market_res.order_id,
                                            fee_tier=fee_tier_obj,
                                        )
                                        bracket_res = await exchange.place_exit_bracket(bracket_req)
                                    except Exception as bracket_e:
                                        logger.error(f"Exit bracket placement FAILED for {event.symbol}: {bracket_e}")
                                        bracket_failed = True

                                    if bracket_failed or not bracket_res:
                                        # ── CASO B: BRACKET FALLITO ──
                                        # Market sell di emergenza con qty reale post-fee
                                        logger.error(f"BRACKET_FLOW CASO B: bracket fallito per {event.symbol} — eseguo market sell emergenza")
                                        await _handle_bracket_failed(exchange, event.symbol.upper())
                                        continue  # Nessun salvataggio DB, nessuna apertura posizione

                                    # ── CASO A: BRACKET RIUSCITO ──
                                    # 3b. Register position AFTER bracket confermato (TASK-827 / TASK-1107)
                                    # TASK-886: propaga la commissione reale dell'entry sulla Position
                                    pos_obj = pm.open_position(
                                        symbol=event.symbol.upper(),
                                        side=side,
                                        entry_price=Decimal(str(exec_price)),
                                        quantity=Decimal(str(exec_qty)),
                                        entry_commission=entry_commission_real if entry_commission_real > 0 else None,
                                        entry_commission_asset=entry_commission_asset_real,
                                    )

                                    # Salva bracket IDs sul position object (provider-neutral)
                                    pos_obj.oco_order_list_id = str(bracket_res.bracket_id or "")
                                    pos_obj.sl_order_id = str(bracket_res.sl_order_id or "")
                                    pos_obj.tp_order_id = str(bracket_res.tp_order_id or "")
                                    # Legacy fields for backward compat
                                    pos_obj.oco_id = bracket_res.bracket_id
                                    pos_obj.sl_id = bracket_res.sl_order_id
                                    pos_obj.tp_id = bracket_res.tp_order_id

                                    # TASK-1129: porta i veri prezzi TP/SL (piazzati sull'exchange
                                    # via bracket) anche sull'oggetto in memoria. Altrimenti il
                                    # sistema li ricalcola da percentuali e mostra valori sballati.
                                    pos_obj.tp_price = Decimal(str(tp_price))
                                    pos_obj.sl_price = Decimal(str(sl_price))

                                    # Persist open position to DB con tp/sl price e OCO IDs (TASK-825)
                                    if supervisor_context:
                                        # Calculate slippage
                                        sig_p = supervisor_context.get("signal_price")
                                        if sig_p and float(sig_p) > 0:
                                            supervisor_context["slippage_pct"] = round(abs(float(exec_price) - sig_p) / sig_p * 100, 4)
                                    await _save_open_position_to_db(
                                        pos_obj, session.get("db_session_id"),
                                        tp_price=tp_price, sl_price=sl_price,
                                        supervisor_context=supervisor_context,
                                        signal_log_id=_signal_log_id,
                                    )

                                    # Avvia UDS singleton post-OCO (TASK-827)
                                    await _start_uds_if_needed()

                                    # Refresh live balance
                                    await _refresh_session_balance()

                                    logger.info(
                                        f"\033[92m🎯 EXIT BRACKET ATTIVO: {side} {event.symbol.upper()} @ {exec_price} | TP={tp_price:.2f} | SL={sl_price:.2f} | provider={settings.EXCHANGE_PROVIDER.upper()}\033[0m"
                                    )

                                    await broadcast_scalping_event("position", {
                                        "symbol": pos_obj.symbol,
                                        "side": pos_obj.side,
                                        "entry_price": float(pos_obj.entry_price),
                                        "current_price": float(candle.close),
                                        "entry_time": pos_obj.entry_time.isoformat(),
                                        "quantity": float(pos_obj.quantity),
                                        "trade_value_usd": round(float(pos_obj.quantity) * float(pos_obj.entry_price), 2),
                                        "pnl": 0.0,
                                        "pnl_pct": 0.0,
                                        "stop_loss_price": round(sl_price, 2),
                                        "take_profit_price": round(tp_price, 2),
                                        "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                                        "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                                    })

                                    # Signal to session stop that we need a close on Binance
                                    _execution_state["pending_live_close"] = True

                                    
                                except Exception as live_e:
                                    # TASK-908: log body completo eccezione Binance
                                    from app.execution.exchange import ExchangeOrderError
                                    if isinstance(live_e, ExchangeOrderError):
                                        # TASK-908: extract preserved original details
                                        error_detail = str(live_e)
                                        if live_e.original_details:
                                            error_detail = f"{error_detail} | Original: {live_e.original_details}"
                                        if live_e.original_exception:
                                            error_detail += f" | Exception: {type(live_e.original_exception).__name__}"
                                    else:
                                        error_detail = f"{type(live_e).__name__}: {live_e}"
                                    logger.error(f"Live trade failed: {error_detail}")
                                    # TASK-894: log execution_error su session_signal_log (non-blocking)
                                    asyncio.create_task(asyncio.to_thread(
                                        log_execution_error,
                                        session_id=session.get("db_session_id") or session.get("session_id") or "",
                                        symbol=event.symbol.upper(),
                                        error_message=error_detail,
                                        regime=execution_loop._current_regime.regime if execution_loop._current_regime else "unknown",
                                        strategy_type=execution_loop._strategy.name if execution_loop._strategy else "unknown",
                                        tech_signal=side,
                                    ))
                                    await broadcast_scalping_event("error", {
                                        "code": "LIVE_TRADE_ERROR",
                                        "message": f"Live trade failed: {error_detail}",
                                    })
                                    continue
                            
                            else:
                                # Paper mode
                                _qty = Decimal(str(round(_trade_val / float(event.close), 6)))
                                pos_obj = pm.open_position(
                                    symbol=event.symbol.upper(),
                                    side=side,
                                    entry_price=Decimal(str(event.close)),
                                    quantity=_qty,
                                )
                                # Persist open position to DB immediately
                                if supervisor_context:
                                    sig_p = supervisor_context.get("signal_price")
                                    if sig_p and float(sig_p) > 0:
                                        supervisor_context["slippage_pct"] = round(abs(float(event.close) - sig_p) / sig_p * 100, 4)
                                await _save_open_position_to_db(pos_obj, session.get("db_session_id"), supervisor_context=supervisor_context, signal_log_id=_signal_log_id)
                                
                                # Update paper balance to reflect Free Balance
                                session["paper_balance"] -= float(_trade_val)
                                await broadcast_scalping_event("session_restored", session.copy())
                                await broadcast_scalping_event("position", {
                                    "symbol": pos_obj.symbol,
                                    "side": pos_obj.side,
                                    "entry_price": float(pos_obj.entry_price),
                                    "current_price": float(candle.close),
                                    "entry_time": pos_obj.entry_time.isoformat(),
                                    "quantity": float(pos_obj.quantity),
                                    "trade_value_usd": round(float(pos_obj.quantity) * float(pos_obj.entry_price), 2),
                                    "pnl": 0.0,
                                    "pnl_pct": 0.0,
                                })
                                logger.info(f">>> TRADE EXECUTED: {side} {event.symbol.upper()} @ {candle.close}")
                        else:
                            # If opposite signal, close position
                            pos = pm.get_open()
                            if pos.side.lower() != side.lower():
                                logger.info(f">>> CLOSING: {pos.side} position opposite to {side} signal")
                                await _close_position_and_record(pm, float(candle.close), pos, reason=decision.reason or "signal")
                            else:
                                logger.info(f">>> HOLD: existing {pos.side} position matches {side} signal")
                                # TASK-894: log hold su session_signal_log (non-blocking)
                                _ms = execution_loop._last_market_score
                                asyncio.create_task(asyncio.to_thread(
                                    log_hold_decision,
                                    session_id=session.get("db_session_id") or session.get("session_id") or "",
                                    symbol=event.symbol.upper(),
                                    hold_reason=f"existing {pos.side} position matches {side} signal",
                                    regime=execution_loop._current_regime.regime if execution_loop._current_regime else "unknown",
                                    strategy_type=execution_loop._strategy.name if execution_loop._strategy else "unknown",
                                    tech_signal=side,
                                    intel_score=float(_ms.total) if _ms else None,
                                    intel_bias=_ms.bias if _ms else None,
                                    trend_direction=_ms.trend_direction if _ms else None,
                                    trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                                ))

                    else:
                        reason_str = decision.reason if decision else "decision=None"
                        logger.info(f">>> DECISION REJECTED: {reason_str}")
                        # TASK-894: log rejected su session_signal_log (non-blocking)
                        if decision and session.get("db_session_id"):
                            _ms = execution_loop._last_market_score
                            # Determina decision_type più specifico dal reason
                            _dtype = "rejected_other"
                            if decision.signal_type == "HOLD":
                                _dtype = "hold_existing_position"
                            elif decision.reason and "conflitto intelligence-tecnico" in decision.reason:
                                _dtype = "block_conflict"
                            elif decision.reason and "MEAN-REVERSION" in decision.reason:
                                _dtype = "mean_reversion_override"
                            asyncio.create_task(asyncio.to_thread(
                                log_signal_decision,
                                session_id=session.get("db_session_id") or "",
                                symbol=event.symbol.upper(),
                                decision_type=_dtype,
                                decision_reason=decision.reason,
                                regime=execution_loop._current_regime.regime if execution_loop._current_regime else "unknown",
                                strategy_type=execution_loop._strategy.name if execution_loop._strategy else "unknown",
                                tech_signal=decision.signal_type or None,
                                intel_score=float(_ms.total) if _ms else None,
                                intel_bias=_ms.bias if _ms else None,
                                trend_direction=_ms.trend_direction if _ms else None,
                                trend_value=float(_ms.trend_5m) if _ms and _ms.trend_5m is not None else None,
                            ))
                except Exception as e:
                    logger.warning(f"Execution loop processing error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                try:
                    # ── FIX-2026-06-05: Position update broadcast on every closed candle ──
                    # This ensures the position card updates in the frontend even in live mode
                    # where trade events may be sporadic. Broadcasts PnL, current price, SL/TP.
                    pm = _execution_state["position_manager"]
                    pos = pm.get_open()
                    if pos:
                        current_price_f = float(event.close)
                        entry_f = float(pos.entry_price)
                        qty_f = float(pos.quantity)
                        entry_val = entry_f * qty_f
                        current_val = current_price_f * qty_f
                        gross_pnl = (current_price_f - entry_f) * qty_f if pos.side == "BUY" else (entry_f - current_price_f) * qty_f
                        
                        # TASK-882: Usa fee tier per PnL non realizzato (Caso B)
                        # Entry: commissione reale se disponibile da WebSocket, altrimenti fee tier
                        if pos.entry_commission is not None and pos.entry_commission > 0:
                            entry_commission = float(pos.entry_commission)
                            # Converti BNB to USDC se necessario
                            exchange = _execution_state.get("exchange")
                            if pos.entry_commission_asset == "BNB" and exchange:
                                entry_commission = await _convert_bnb_commission_to_usdc(
                                    exchange, entry_commission, context="Position update (loop): "
                                )
                        else:
                            # Fallback: usa fee tier per entrata (costo atteso)
                            fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                            entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
                            entry_commission = entry_val * entry_fee_rate
                        
                        # Exit: usa fee tier (costo di chiusura atteso al tier corrente)
                        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                        exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO orders = maker
                        exit_commission = current_val * exit_fee_rate
                        
                        total_fees = entry_commission + exit_commission
                        pnl = gross_pnl - total_fees
                        pnl_pct = (pnl / entry_val) * 100
                        
                        risk_cfg = _execution_state.get("risk_config", {})
                        _sl_cfg = float(risk_cfg.get("stop_loss_pct", 0.3))
                        _tp_cfg = float(risk_cfg.get("take_profit_pct", 0.5))
                        _ft3 = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                        _ef3, _xf3 = _ft3.get("taker", 0.001), _ft3.get("maker", 0.001)
                        # TASK-1127: Fees are now positive for base level accounts
                        sl_price = entry_f * (1 + _net_to_gross_pct(-_sl_cfg, _ef3, _xf3) / 100) if pos.side == "BUY" else entry_f * (1 - _net_to_gross_pct(-_sl_cfg, _ef3, _xf3) / 100)
                        tp_price = entry_f * (1 + _net_to_gross_pct(_tp_cfg, _ef3, _xf3) / 100) if pos.side == "BUY" else entry_f * (1 - _net_to_gross_pct(_tp_cfg, _ef3, _xf3) / 100)
                        # TASK-1129: usa i veri prezzi TP/SL piazzati su OKX se disponibili
                        # (fallback al ricalcolo da percentuali per posizioni pre-fix / restore).
                        if pos.sl_price is not None:
                            sl_price = float(pos.sl_price)
                        if pos.tp_price is not None:
                            tp_price = float(pos.tp_price)
                        
                        # TASK-885: Calcola target netti TP/SL (fee tier round-trip)
                        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                        entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
                        exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO orders = maker
                        fee_round_trip = (entry_fee_rate + exit_fee_rate) * 100  # converti in percentuale
                        
                        # Calcola percentuali nette (sottrai fee round-trip dai target lordi)
                        sl_pct_net = (_sl_cfg) - fee_round_trip  # perdita netta è peggiore
                        tp_pct_net = (_tp_cfg) - fee_round_trip  # guadagno netto è minore
                        
                        # Calculate progress percentage:
                        # -100% = at SL, 0% = at entry, +100% = at TP
                        if pos.side == "BUY":
                            total_range = tp_price - sl_price
                            current_offset = current_price_f - entry_f  # positive if above entry
                        else:
                            total_range = sl_price - tp_price
                            current_offset = entry_f - current_price_f  # positive if below entry
                        
                        progress_pct = 0.0
                        if total_range > 0:
                            if pos.side == "BUY":
                                # How far from entry towards TP or SL
                                if current_price_f >= entry_f:
                                    progress_pct = ((current_price_f - entry_f) / (tp_price - entry_f)) * 100
                                else:
                                    progress_pct = -((entry_f - current_price_f) / (entry_f - sl_price)) * 100
                            else:
                                if current_price_f <= entry_f:
                                    progress_pct = ((entry_f - current_price_f) / (entry_f - tp_price)) * 100
                                else:
                                    progress_pct = -((current_price_f - entry_f) / (sl_price - entry_f)) * 100
                        
                        # Clamp to [-100, 100]
                        progress_pct = max(-100.0, min(100.0, progress_pct))
                        
                        await broadcast_scalping_event("position_update", {
                            "symbol": pos.symbol,
                            "side": pos.side,
                            "entry_price": entry_f,
                            "current_price": round(current_price_f, 2),
                            "quantity": qty_f,
                            "trade_value_usd": round(qty_f * entry_f, 2),
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "stop_loss_price": round(sl_price, 2),
                            "take_profit_price": round(tp_price, 2),
                            "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                            "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                            "stop_loss_pct_net": round(sl_pct_net, 2),  # TASK-885
                            "take_profit_pct_net": round(tp_pct_net, 2),  # TASK-885
                            "progress_pct": round(progress_pct, 1),         # -100 to +100
                            "sl_distance_pct": round(max(0, (entry_f - current_price_f) / (entry_f - sl_price) * 100) if pos.side == "BUY" and (entry_f - sl_price) > 0 else 0, 1),
                            "tp_distance_pct": round(min(100, (current_price_f - entry_f) / (tp_price - entry_f) * 100) if pos.side == "BUY" and (tp_price - entry_f) > 0 else 0, 1),
                        })
                        logger.debug(f"Position update broadcast @ {current_price_f}: PnL={pnl:.2f} ({pnl_pct:.2f}%) progress={progress_pct:.1f}%")
                except Exception as e:
                    logger.error(f"Error in position broadcast: {e}")
            else:
                logger.debug(f">>> LIVE candle update (not closed yet): {event.symbol} close={event.close}")

    async def _trade_processor():
        """Consume trade_queue and broadcast + update PnL + feed CVD."""
        _cvd = _execution_state.get("cvd_calculator")
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            try:
                event = await asyncio.wait_for(client.trade_queue.get(), timeout=1.0)
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
                    _ef4, _xf4 = _ft4.get("taker", 0.001), _ft4.get("maker", 0.001)
                    # TASK-1127: Fees are now positive for base level accounts
                    sl = entry * (1 + _net_to_gross_pct(-_sl_cfg4, _ef4, _xf4) / 100) if pos.side == "BUY" else entry * (1 - _net_to_gross_pct(-_sl_cfg4, _ef4, _xf4) / 100)
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
                        entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
                        entry_commission = entry_val * entry_fee_rate
                    
                    # Exit: usa fee tier (costo di chiusura atteso al tier corrente)
                    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                    exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO orders = maker
                    exit_commission = current_val * exit_fee_rate
                    
                    total_fees = entry_commission + exit_commission
                    pnl = gross_pnl - total_fees
                    pnl_pct = (pnl / entry_val) * 100
                    await broadcast_scalping_event("position_update", {
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "entry_price": entry,
                        "current_price": current,
                        "quantity": qty,
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 2),
                        "stop_loss_price": round(sl, 2),
                        "take_profit_price": round(tp, 2),
                        "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                        "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
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


    async def _intelligence_processor():
        """Poll intelligence and broadcast."""
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            if _execution_state["session"]["status"] == "running":
                try:
                    snapshot = await signal_engine.get_snapshot()
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

    # ── Start SupervisorScheduler (ONLY in restore_mode; for normal start it's done in _start_with_error_logging) ──
    if restore_mode:
        try:
            from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler
            supervisor = SupervisorScheduler(symbol=symbol, interval_seconds=settings.scalping.SCALPING_SUPERVISOR_INTERVAL_SEC, score_engine=_execution_state.get("signal_engine"))
            _execution_state["loop"].session_id = _execution_state["session"].get("db_session_id")
            supervisor.set_execution_loop(_execution_state["loop"])
            supervisor.start()
            _execution_state["supervisor_scheduler"] = supervisor
            logger.info(f"SupervisorScheduler started for {symbol} (restore_mode)")
        except Exception as e:
            logger.warning(f"Failed to start SupervisorScheduler in restore_mode: {e}")

        # ── FIX: avvia UDS se c'è una posizione aperta (TASK-827/TASK-830)
        # In restore_mode l'UDS non viene avviato dal candle_processor perché non
        # passiamo per il Caso A (OCO confermato). Deve partire subito se la posizione
        # è già aperta, altrimenti i fill TP/SL su Binance non vengono recepiti.
        pm = _execution_state["position_manager"]
        if pm.has_open() and _execution_state["session"].get("mode") == "live":
            try:
                await _start_uds_if_needed()
                logger.info(f"UDS avviato in restore_mode per posizione aperta su {symbol}")
            except Exception as uds_e:
                logger.warning(f"Failed to start UDS in restore_mode: {uds_e}")

    # Start processor tasks
    _session_mode = _execution_state["session"].get("mode", "paper")
    task_candle = asyncio.create_task(_candle_processor(), name=f"candle-proc-{symbol}")
    task_trade = asyncio.create_task(_trade_processor(), name=f"trade-proc-{symbol}")
    task_intel = asyncio.create_task(_intelligence_processor(), name=f"intel-proc-{symbol}")

    _execution_state["ws_tasks"] = [task_candle, task_trade, task_intel]

    # Log how many frontend WS clients are connected
    ws_count = len(_scalping_ws_connections)
    logger.info(f"Scalping broadcast started for {symbol} — {ws_count} frontend WS client(s) connected")
    logger.info(f">>> _start_ws_broadcast() COMPLETE for {symbol}")


@router.get("/binance/exchange-info")
async def binance_exchange_info():
    """Proxy Binance exchangeInfo to frontend (avoids CORS).
    Returns only the fields the frontend needs: symbol, status, baseAsset, quoteAsset.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.binance.com/api/v3/exchangeInfo")
            resp.raise_for_status()
            data = resp.json()
        # Slim down: only TRADING + stablecoin quote assets
        allowed_quotes = {"USDT", "USDC", "FDUSD", "EUR"}
        symbols = [
            {
                "symbol": s["symbol"],
                "status": s["status"],
                "baseAsset": s["baseAsset"],
                "quoteAsset": s["quoteAsset"],
            }
            for s in data.get("symbols", [])
            if s.get("quoteAsset") in allowed_quotes and s.get("status") == "TRADING"
        ]
        return {"symbols": symbols}
    except Exception as e:
        logger.error(f"Failed to proxy Binance exchangeInfo: {e}")
        raise HTTPException(status_code=502, detail=f"Binance API unreachable: {e}")




@router.get("/exchange/instruments")
async def exchange_instruments():
    """TASK-1109: Provider-neutral instruments endpoint.

    OKX: returns live spot pairs via /api/v5/public/instruments.

    Binance: proxies Binance exchangeInfo.

    """

    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        import httpx
        base_url = settings.OKX_BASE_URL.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base_url}/api/v5/public/instruments",
                    params={"instType": "SPOT"},
                )
                resp.raise_for_status()
                data = resp.json()
            raw = data.get("data", [])
            instruments = [
                {
                    "symbol": item["instId"],
                    "base": item["baseCcy"],
                    "quote": item["quoteCcy"],
                    "status": item.get("state", "live"),
                    "provider": "okx",
                }
                for item in raw
                if item.get("state") == "live"
            ]
            instruments.sort(key=lambda x: (x["quote"] != "EUR", x["symbol"]))
            eur_pairs = [i["symbol"] for i in instruments if i["quote"] == "EUR"]
            default_symbol = "BTC-EUR" if "BTC-EUR" in eur_pairs else (eur_pairs[0] if eur_pairs else "BTC-EUR")
            return {
                "provider": "okx",
                "demo": settings.exchange_demo,
                "default_symbol": default_symbol,
                "instruments": instruments,
            }
        except Exception as e:
            logger.error(f"Failed to fetch OKX instruments: {e}")
            raise HTTPException(status_code=502, detail=f"OKX API unreachable: {e}")
    else:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://api.binance.com/api/v3/exchangeInfo")
                resp.raise_for_status()
                data = resp.json()
            allowed_quotes = {"USDT", "USDC", "FDUSD", "EUR"}
            instruments = [
                {"symbol": s["symbol"], "base": s["baseAsset"], "quote": s["quoteAsset"], "status": s["status"], "provider": "binance"}
                for s in data.get("symbols", [])
                if s.get("quoteAsset") in allowed_quotes and s.get("status") == "TRADING"
            ]
            instruments.sort(key=lambda x: x["symbol"])
            eur_pairs = [i["symbol"] for i in instruments if i["quote"] == "EUR"]
            usdc_pairs = [i["symbol"] for i in instruments if i["quote"] == "USDC"]
            default_symbol = eur_pairs[0] if eur_pairs else (usdc_pairs[0] if usdc_pairs else "BTCUSDC")
            return {"provider": "binance", "demo": False, "default_symbol": default_symbol, "instruments": instruments}
        except Exception as e:
            logger.error(f"Failed to proxy Binance exchangeInfo: {e}")
            raise HTTPException(status_code=502, detail=f"Binance API unreachable: {e}")

@router.get("/sessions")
async def list_scalping_sessions(limit: int = 50, offset: int = 0) -> List[Dict]:
    """TASK-880: Lista sessioni scalping storiche, arricchite con totali reali dai trade."""
    try:
        supabase = get_supabase()
        resp = supabase.table("scalping_sessions") \
            .select("id, symbol, mode, status, started_at, stopped_at, total_pnl, trade_count, win_count, strategy, trade_value") \
            .order("started_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        rows = resp.data or []

        # Per ogni sessione: calcola duration_seconds e arricchisci trade_count/pnl dai trade reali
        session_ids = [r["id"] for r in rows]
        trades_by_session: Dict[str, list] = {}
        if session_ids:
            try:
                tr = supabase.table("scalping_trades") \
                    .select("session_id, pnl, signal_reason, status, entry_price, exit_price, entry_time, quantity") \
                    .in_("session_id", session_ids) \
                    .eq("status", "closed") \
                    .execute()
                for t in (tr.data or []):
                    sid = t["session_id"]
                    trades_by_session.setdefault(sid, []).append(t)
            except Exception as te:
                logger.warning(f"list_sessions trades enrichment error: {te}")

        from datetime import datetime as _dt
        for row in rows:
            # duration
            started = row.get("started_at")
            stopped = row.get("stopped_at")
            if started and stopped:
                try:
                    s = _dt.fromisoformat(started.replace("Z", "+00:00"))
                    e = _dt.fromisoformat(stopped.replace("Z", "+00:00"))
                    row["duration_seconds"] = int((e - s).total_seconds())
                except Exception:
                    row["duration_seconds"] = None
            else:
                row["duration_seconds"] = None

                # Arricchisci con dati reali dai trade (override se trade_count == 0)
            session_trades = trades_by_session.get(row["id"], [])
            if session_trades:
                row["trade_count"] = len(session_trades)
                row["win_count"] = len([t for t in session_trades if (t.get("pnl") or 0) > 0])
                row["total_pnl"] = round(sum((t.get("pnl") or 0) for t in session_trades), 4)
                # Calcola total_pnl_pct sull'effettivo capitale allocato per singolo trade, non sulla somma
                allocated_capital = float(row.get("trade_value") or 0)
                if allocated_capital <= 0:
                    allocated_capital = float(row.get("paper_balance") or 10000.0)
                row["total_pnl_pct"] = round(
                    (row["total_pnl"] / allocated_capital) * 100, 2
                ) if allocated_capital > 0 else None
                # Calcola vs Hold: (exit_price ultimo trade / entry_price primo trade - 1) * 100
                sorted_trades = sorted(session_trades, key=lambda t: t.get("entry_time") or "")
                first_entry = float(sorted_trades[0].get("entry_price") or 0)
                last_exit = float(sorted_trades[-1].get("exit_price") or 0)
                if first_entry > 0 and last_exit > 0:
                    row["hold_pnl_pct"] = round((last_exit - first_entry) / first_entry * 100, 2)
                else:
                    row["hold_pnl_pct"] = None

        return rows
    except Exception as e:
        logger.warning(f"list_scalping_sessions error: {e}")
        return []


@router.get("/trade-history")
async def get_trade_history(session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """TASK-881: Trade history. Se session_id fornito: query DB. Altrimenti: memoria corrente."""
    if session_id:
        try:
            supabase = get_supabase()
            resp = supabase.table("scalping_trades") \
                .select("symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, entry_time, exit_time, signal_reason, status") \
                .eq("session_id", session_id) \
                .order("entry_time", desc=True) \
                .limit(limit) \
                .execute()
            return resp.data or []
        except Exception as e:
            logger.warning(f"get_trade_history DB error: {e}")
            return []

    # Comportamento originale: in-memory, aggiunge entry_time/exit_time dagli alias
    trades = _execution_state["trade_history"]
    closed_trades = [t for t in trades if t.get("exit_price") is not None]
    sorted_trades = sorted(closed_trades, key=lambda t: t.get("timestamp", ""), reverse=True)
    result = []
    for t in sorted_trades[:limit]:
        row = dict(t)
        row.setdefault("entry_time", t.get("timestamp"))
        row.setdefault("exit_time", t.get("timestamp"))
        result.append(row)
    return result


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, limit: int = 100) -> List[Dict]:
    """Get candle history for a symbol. ..."""
    try:
        from app.scalping.backtest.historical_loader import HistoricalLoader
        loader = HistoricalLoader()
        past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=limit)
        if past_candles:
            result = [
                {
                    "symbol": symbol,
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close),
                    "volume": float(c.volume),
                    "timestamp": c.timestamp.isoformat(),
                }
                for c in past_candles
            ]
            logger.info(f"Returning {len(result)} candles from HistoricalLoader for {symbol}")
            return result
        return []  # <-- ADD THIS: handles the empty/falsy past_candles case
    except Exception as e:
        logger.warning(f"HistoricalLoader fetch failed for {symbol}: {e}")
        return []


async def _stop_ws_broadcast():
    """Stop WS client and clean up pipeline components."""
    client = _execution_state.get("ws_client")
    if client:
        await client.stop()
        _execution_state["ws_client"] = None
    
    loop = _execution_state.get("loop")
    if loop:
        await loop.stop()
        _execution_state["loop"] = None
    
    _execution_state["signal_engine"] = None
    _execution_state["cvd_calculator"] = None

    # Cancel all WS tasks
    for task in _execution_state.get("ws_tasks", []):
        task.cancel()
    _execution_state["ws_tasks"] = []


# ---------------------------------------------------------------------------
# Backtest endpoints (from TASK-808)
# ---------------------------------------------------------------------------

@router.post("/backtest/run")
async def run_backtest(config: BacktestConfig) -> Dict:
    """Esegue un backtest per la configurazione specificata."""
    try:
        loader = HistoricalLoader()
        candles = await loader.load_ohlcv(
            symbol=config.symbol,
            interval=config.timeframe,
            start=config.start_date,
            end=config.end_date,
            limit=1000,
        )

        if not candles:
            raise HTTPException(
                status_code=400,
                detail=f"Nessun dato storico trovato per {config.symbol} "
                       f"da {config.start_date.date()} a {config.end_date.date()}.",
            )

        engine = BacktestEngine()
        result = await engine.run(config, candles=candles)

        calculator = PerformanceCalculator()
        calculator.calculate(result)
        calculator.calculate_correlation(result)

        generator = ReportGenerator(calculator=calculator)
        report = generator.generate_report(result)

        result_id = str(uuid.uuid4())[:8]
        _backtest_results[result_id] = result
        report["config"]["result_id"] = result_id

        logger.info(f"Backtest {result_id} completed: {len(result.trades)} trades, "
                     f"PnL={result.metrics.get('total_pnl', 0):.2f} USDT")

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")


@router.get("/backtest/{result_id}/result")
async def get_backtest_result(result_id: str) -> Dict:
    """Recupera il risultato di un backtest completato."""
    result = _backtest_results.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Backtest {result_id} non trovato.")

    generator = ReportGenerator()
    report = generator.generate_report(result)
    report["config"]["result_id"] = result_id
    return report


@router.get("/backtest/list")
async def list_backtests() -> List[Dict]:
    """Lista tutti i backtest eseguiti nella sessione corrente."""
    summaries = []
    for rid, result in _backtest_results.items():
        m = result.metrics
        summaries.append({
            "id": rid,
            "symbol": result.config.symbol,
            "start_date": result.config.start_date.isoformat(),
            "end_date": result.config.end_date.isoformat(),
            "total_trades": m.get("total_trades", 0),
            "total_pnl": m.get("total_pnl", 0),
            "win_rate": m.get("win_rate", 0),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        })
    return summaries


# ---------------------------------------------------------------------------
# Intelligence endpoints (connessi a SignalScoreEngine)
# ---------------------------------------------------------------------------

@router.get("/intelligence/{symbol}/snapshot")
async def get_intel_snapshot(symbol: str) -> Dict:
    """Get latest market intelligence snapshot for symbol.
    
    Se SignalScoreEngine è inizializzato, usa quello;
    altrimenti restituisce un fallback leggero.
    Include funding_rate, open_interest, fear_greed, cvd_trend
    per il pannello Market Intelligence del frontend.
    """
    engine = _execution_state.get("signal_engine")
    
    # Try to get full snapshot (score + raw data)
    if engine and engine.symbol == symbol:
        try:
            snapshot = await engine.get_snapshot()
            return _snapshot_to_dict(symbol, snapshot)
        except Exception:
            logger.warning(f"SignalScoreEngine failed for {symbol}, using fallback")
    
    # Fallback: prova a creare engine on-the-fly
    try:
        fallback_engine = SignalScoreEngine(symbol=symbol)
        snapshot = await fallback_engine.get_snapshot()
        return _snapshot_to_dict(symbol, snapshot)
    except Exception as e:
        logger.debug(f"Fallback engine failed: {e}")
    
    # Ultimate fallback
    return {
        "symbol": symbol,
        "funding_rate": 0.0,
        "open_interest": 0,
        "long_pct": 0,
        "short_pct": 0,
        "cvd_trend": "neutral",
        "fear_greed_value": 50,
        "fear_greed_label": "Neutral",
        "signal_score": 50.0,
        "signal_bias": "neutral",
        "tradeable": False,
        "breakdown": {},
        "recorded_at": _now(),
    }


@router.get("/intelligence/{symbol}/history")
async def get_intel_history(symbol: str, limit: int = 100) -> List[Dict]:
    """Get historical intelligence snapshots from Supabase."""
    try:
        supabase = get_supabase()
        response = supabase.table("market_intel_snapshots") \
            .select("*") \
            .eq("symbol", symbol) \
            .order("recorded_at", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        logger.warning(f"Failed to fetch intel history from DB: {e}")
        return []


def _snapshot_to_dict(symbol: str, snapshot: Any) -> Dict[str, Any]:
    """Converte MarketIntelSnapshot in dict per risposta API,
    includendo sia lo score aggregato che i dati grezzi dei collector.
    """
    result: Dict[str, Any] = {
        "symbol": symbol,
        "recorded_at": _now(),
    }
    
    # Score aggregato
    if snapshot.signal_score:
        score = snapshot.signal_score
        result["signal_score"] = score.total
        result["signal_bias"] = score.bias
        result["tradeable"] = score.tradeable
        result["confidence"] = score.signal_strength or 0.0
        result["breakdown"] = score.breakdown
    
    # Dati grezzi dai collector (per il pannello Market Intelligence)
    if snapshot.funding_rate:
        result["funding_rate"] = float(snapshot.funding_rate.rate)
    if snapshot.open_interest:
        result["open_interest"] = float(snapshot.open_interest.value_usd)
    if snapshot.fear_greed:
        result["fear_greed_value"] = snapshot.fear_greed.value
        result["fear_greed_label"] = snapshot.fear_greed.label
    if snapshot.cvd:
        result["cvd_trend"] = snapshot.cvd.trend or "neutral"
    if snapshot.long_short_ratio:
        result["long_pct"] = float(snapshot.long_short_ratio.long_pct)
        result["short_pct"] = float(snapshot.long_short_ratio.short_pct)
    
    return result


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

def _calc_session_entry_and_hold(trade_history: List[Dict], current_price: Optional[float] = None):
    """Calcola prezzo primo trade della sessione e hold PnL vs current price.
    
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


@router.get("/health")
async def scalping_health() -> Dict:
    """Health check per tutti i componenti del modulo scalping (TASK-865)."""
    session = _execution_state["session"]
    ws_client = _execution_state.get("ws_client")
    uds = _execution_state.get("user_data_stream")
    supervisor = _execution_state.get("supervisor_scheduler")
    loop = _execution_state.get("loop")
    signal_engine = _execution_state.get("signal_engine")
    guard = _execution_state.get("session_load_guard")

    return {
        "session_status": session.get("status"),
        "ws_client": {
            "connected": ws_client is not None and not ws_client._stop_event.is_set(),
            "symbol": session.get("symbol"),
        },
        "uds": {
            "active": uds is not None,
            "running": uds._running if uds else False,
        },
        "supervisor": {
            "active": supervisor._running if supervisor else False,
            "interval_sec": supervisor._interval if supervisor else None,
            "daily_calls": supervisor._daily_ai_calls if supervisor else 0,
        },
        "candle_buffer": {
            "size": len(loop._candle_buffer) if loop and loop._candle_buffer else 0,
            "ready": loop._candle_buffer.is_ready() if loop and loop._candle_buffer else False,
        },
        "signal_engine": {
            "symbol": signal_engine.symbol if signal_engine else None,
            "active": signal_engine is not None,
        },
        "session_guard": guard.monitor_data if guard else {},
    }


@router.get("/session")
async def get_session() -> Dict:
    """Get current session status.
    
    For live sessions, automatically refreshes the balance from the exchange
    so the frontend always shows the real balance, not a stale one.
    """
    session = _execution_state["session"]
    # Refresh live balance if mode is live and exchange is initialized
    if session.get("status") == "running" and session.get("mode") == "live":
        await _refresh_session_balance()
    result = session.copy()
    guard = _execution_state.get("session_load_guard")
    if guard:
        result["load_guard"] = guard.monitor_data
    
    # Aggiungi entry price e hold PnL (calcolati dai trade history)
    loop = _execution_state.get("loop")
    current_price = None
    if loop and hasattr(loop, "_candle_buffer") and loop._candle_buffer and loop._candle_buffer.latest:
        current_price = float(loop._candle_buffer.latest.close)
    first_entry, hold_pnl = _calc_session_entry_and_hold(
        _execution_state.get("trade_history", []),
        current_price,
    )
    result["first_trade_entry"] = first_entry
    result["hold_pnl_pct"] = hold_pnl
    result["fee_tier_certified"] = _execution_state.get("fee_tier_certified", None)
    # Add current signal threshold so frontend can show score/threshold
    try:
        result["signal_strength_threshold"] = get_scalping_config().signal_strength_threshold
    except Exception:
        result["signal_strength_threshold"] = None
    
    return result


@router.post("/session")
async def control_session(control: Dict) -> Dict:
    """Control session: start, stop, pause, resume."""
    session = _execution_state["session"]
    action = control.get("action")

    if action == "start":
        guard = _execution_state.get("session_load_guard")
        if guard:
            guard.reset()
            guard.start_loading()

        active_symbol = control.get("symbol", session.get("symbol", "BTCUSDT"))

        # ── LIVE/DEMO MODE: verify balance BEFORE setting session state ────────────
        # TASK-1107: provider-neutral — build adapter via factory (OKX or Binance).
        # Prevent stale state when balance check fails (HTTPException would leave
        # a dirty session in memory, confusing the frontend on reconnect).
        session_mode = control.get("mode", session.get("mode", "paper"))
        if session_mode in ("live", "test"):
            if not settings.exchange_api_key or not settings.exchange_secret_key:
                raise HTTPException(status_code=400, detail="Mancano le API Key nel file .env per la modalità Live/Demo.")

            # TASK-1107: use factory — returns OkxExchangeAdapter or BinanceExchangeAdapter
            from app.execution.exchange_factory import build_exchange_adapter
            adapter = build_exchange_adapter()

            try:
                # Get quote asset from symbol (e.g. BTC-EUR -> EUR, BTCUSDT -> USDT)
                from app.execution.exchange_models import SymbolRef
                try:
                    sym_ref = SymbolRef.from_okx(active_symbol) if "-" in active_symbol else SymbolRef.from_compact(active_symbol)
                    quote_asset = sym_ref.quote
                except Exception:
                    quote_asset = "EUR"  # fallback for OKX default

                available_balance = await adapter.get_balance(quote_asset)
                trade_val = float(control.get("trade_value", session.get("trade_value", 10.0)))

                if available_balance is not None and available_balance > 0 and available_balance >= trade_val:
                    _execution_state["exchange"] = adapter
                    session["live_balance"] = available_balance
                    session["paper_balance"] = available_balance
                    mode_label = "DEMO" if session_mode == "test" else "LIVE"
                    logger.info(f"✓ \033[96m\033[1mStarting balance: {available_balance} {quote_asset} [{settings.EXCHANGE_PROVIDER.upper()} {mode_label}]\033[0m")

                    # TASK-877/1114: Recupera fee tier account all'avvio sessione
                    # OKX returns negative fees (rebates): maker=-0.002 means -0.2% rebate.
                    try:
                        sym_ref_for_fee = SymbolRef.from_okx(active_symbol) if "-" in active_symbol else SymbolRef.from_compact(active_symbol)
                        fee_tier_obj = await adapter.get_trade_fee(sym_ref_for_fee)
                        fee_tier = {"maker": fee_tier_obj.maker, "taker": fee_tier_obj.taker}
                        _execution_state["fee_tier"] = fee_tier
                        _execution_state["fee_tier_certified"] = fee_tier_obj.certified
                        logger.info(f"✓ Fee tier [{settings.EXCHANGE_PROVIDER}]: maker={fee_tier_obj.maker}, taker={fee_tier_obj.taker} certified={fee_tier_obj.certified}")
                    except Exception as e:
                        logger.error(f"Impossibile recuperare fee tier reale: {e} — uso default 0.001 NON CERTIFICATO")
                        _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}
                        _execution_state["fee_tier_certified"] = False
                else:
                    error_msg = (
                        f"Nessun saldo Spot disponibile per {quote_asset} (trovato: {available_balance}). "
                        f"I fondi potrebbero essere in Simple Earn. Spostali su Spot e riprova."
                    )
                    mode_label = "DEMO" if session_mode == "test" else "LIVE"
                    logger.error(f"\033[91m✗ {mode_label} START BLOCKED: {error_msg}\033[0m")
                    session["live_balance"] = None
                    session["paper_balance"] = None
                    session["status"] = "idle"
                    session["error_message"] = error_msg
                    session["error_code"] = f"{mode_label}_START_BLOCKED"
                    if guard:
                        guard.fail(f"{session_mode}_start_blocked: insufficient_spot_balance")
                        _sync_session_load_guard()
                    # Close the exchange adapter to prevent resource leak
                    try:
                        await adapter.close()
                    except Exception:
                        pass
                    # Return idle session with error details (frontend will show error toast via sessionRestored$)
                    return session.copy()
            except HTTPException:
                raise
            except Exception as e:
                error_msg = f"Impossibile verificare il saldo Spot: {type(e).__name__}. Riprova."
                logger.error(f"✗ Balance fetch failed: {e}", exc_info=True)
                await broadcast_scalping_event("error", {"code": f"{session_mode.upper()}_START_BALANCE_FETCH_FAILED", "message": error_msg})
                raise HTTPException(status_code=400, detail=error_msg)

        # ── Set session state (balance is verified) ───────────────────────────
        _sync_session_load_guard()
        session["status"] = "running"
        session["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
        session["mode"] = control.get("mode", session.get("mode", "paper"))
        session["strategy"] = control.get("strategy", "scalping_v2")
        session["symbol"] = active_symbol
        session["trade_value"] = float(control.get("trade_value", session.get("trade_value", 10.0)))
        session["started_at"] = _now()
        session["stopped_at"] = None
        # Clear any previous error state from failed start attempts
        session["error_code"] = None
        session["error_message"] = None
        _execution_state["trade_history"] = []
        _execution_state["position_manager"] = PositionManager()
        
        # TASK-877: Inizializza fee tier (default per paper trading, sovrascritto per live)
        if session["mode"] != "live":
            _execution_state["fee_tier"] = {"maker": 0.001, "taker": 0.001}  # default paper
        
        # Reset strategy override if there's an existing execution loop
        existing_loop = _execution_state.get("loop")
        if existing_loop:
            existing_loop.reset_strategy_override()
        
        if guard:
            guard.complete_phase("exchange_phase")
            guard.complete_phase("position_phase")

        # Store trade_value from UI (USD amount per trade)
        if "trade_value" in control:
            try:
                session["trade_value"] = max(1.0, float(control["trade_value"]))
            except (TypeError, ValueError):
                pass  # keep existing value

        # Initialize SignalScoreEngine for the symbol (usando singleton)
        try:
            _execution_state["signal_engine"] = SignalScoreEngine.get_or_create(symbol=active_symbol)
        except Exception as e:
            logger.warning(f"Could not initialize SignalScoreEngine: {e}")

        # NOTE (TASK-827): UDS non viene avviato qui.
        # Viene avviato da _start_uds_if_needed() DOPO che l'OCO è confermato.
        # Questo evita che UDS sia attivo senza ordini e rispetta il pattern singleton.

        # Start WS client + ExecutionLoop pipeline
        async def _start_with_error_logging():
            """Wrapper that logs any exception from _start_ws_broadcast."""
            try:
                await _start_ws_broadcast(active_symbol.lower())
                
                # Guard: check if session is still running BEFORE saving to DB
                # Prevents race condition where user clicked stop while this task was starting
                if session.get("status") != "running":
                    logger.warning("Session status changed during broadcast startup — skipping DB insert (session already stopped by user)")
                    return
                
                # Save to Supabase after successful start
                try:
                    supabase = get_supabase()
                    db_resp = supabase.table("scalping_sessions").insert({
                        "symbol": session["symbol"],
                        "mode": session["mode"].upper(),
                        "timeframe": "1m",
                        "status": "running",
                        "started_at": session["started_at"],
                        "strategy": session.get("strategy", "scalping_v2"),
                        "trade_value": session.get("trade_value", 100.0),
                        # TASK-1108: provider-neutral fields
                        "exchange_provider": settings.EXCHANGE_PROVIDER.lower(),
                        "exchange_account_mode": settings.TRADING_MODE,
                        "exchange_demo": settings.exchange_demo,
                        "fee_tier_certified": _execution_state.get("fee_tier_certified"),
                        "fee_tier_maker": (_execution_state.get("fee_tier") or {}).get("maker"),
                        "fee_tier_taker": (_execution_state.get("fee_tier") or {}).get("taker"),
                    }).execute()
                    if db_resp.data:
                        session["db_session_id"] = db_resp.data[0]["id"]
                        logger.info(f"Session saved to DB with id={session['db_session_id']} mode={session['mode']} trade_value={session.get('trade_value')}")
                        if guard:
                            guard.complete_phase("db_phase")
                    elif guard:
                        guard.fail("db_insert_failed: empty response")
                except Exception as db_e:
                    logger.warning(f"Failed to insert session in DB: {db_e}")
                    if guard:
                        guard.fail(f"db_insert_failed: {type(db_e).__name__}: {db_e}")
                    
                # Start SupervisorScheduler
                from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler
                supervisor = SupervisorScheduler(symbol=active_symbol, interval_seconds=settings.scalping.SCALPING_SUPERVISOR_INTERVAL_SEC, score_engine=_execution_state.get("signal_engine"))
                # Attach db_session_id (UUID) so the supervisor can log it to DB
                _execution_state["loop"].session_id = session.get("db_session_id")
                supervisor.set_execution_loop(_execution_state["loop"])
                supervisor.start()
                _execution_state["supervisor_scheduler"] = supervisor
                    
            except Exception as e:
                if guard:
                    guard.fail(f"broadcast_start_failed: {type(e).__name__}: {e}")
                logger.error(f"Scalping broadcast start FAILED for {active_symbol}: {e}", exc_info=True)
                # Reset session if broadcast failed to start
                session["status"] = "idle"
                session["session_id"] = None
                session["started_at"] = None

        task = asyncio.create_task(
            _start_with_error_logging(),
            name=f"scalping-ws-{active_symbol}",
        )
        # Log exception if task fails silently
        task.add_done_callback(lambda t: logger.error(f"Scalping broadcast task crashed: {t.exception()}") if t.exception() else None)
        
        # ── SESSION LOGGING: attach session_id to all logs + start capture ──
        SessionContextFilter.set_session_id(session["session_id"])
        db_sid = session.get("db_session_id", "")
        session_log_handler = SessionLogHandler(
            session_id=session["session_id"],
            db_session_id=db_sid,
        )
        session_log_handler.symbol = active_symbol
        session_log_handler.attach()  # aggancia root + forced logger
        
        # Soluzione 1: Configura callback per persistenza live su DB
        _handler_logger = logger  # capture reference for closure
        def _make_persist_callback(h: SessionLogHandler) -> Callable[[str], None]:
            """Crea un callback sincrono che salva il contenuto su DB via asyncio thread."""
            import functools
            _db_sid = h.db_session_id
            def _save_to_db(content: str) -> None:
                if not _db_sid:
                    return
                try:
                    from app.db.supabase_client import get_supabase
                    supabase = get_supabase()
                    supabase.table("scalping_sessions").update({
                        "log_content": content,
                    }).eq("id", _db_sid).execute()
                except Exception as e:
                    _handler_logger.warning(f"[LIVE_LOG] Failed to persist logs to DB: {e}")
            return _save_to_db
        
        if db_sid:
            session_log_handler.set_persist_callback(_make_persist_callback(session_log_handler))
            logger.info(f"[LIVE_LOG] Persist callback configured for session {db_sid}")
        
        _execution_state["session_log_handler"] = session_log_handler
        logger.info(f"Session log capture started for {session['session_id']}")
        
        # Soluzione 1: Avvia il task periodico di persistenza log (ogni 5 min)
        _LOG_PERSIST_INTERVAL_SEC = 300  # 5 minuti
        async def _periodic_log_persist():
            """Task asincrono che salva i log su DB ogni 5 minuti.
            
            Se il backend crasha/riavvia, i log salvati fino all'ultimo persist
            sono comunque recuperabili dal DB (non più persi completamente).
            """
            while session.get("status") == "running":
                await asyncio.sleep(_LOG_PERSIST_INTERVAL_SEC)
                handler = _execution_state.get("session_log_handler")
                if handler and handler.log_count > 0:
                    ok = handler.persist_now()
                    if ok:
                        _handler_logger.info(f"[LIVE_LOG] Periodic persist OK ({handler.log_count} entries)")
                    else:
                        _handler_logger.debug("[LIVE_LOG] Periodic persist skipped (no callback or empty)")
        
        _persist_task = asyncio.create_task(_periodic_log_persist(), name="log-persist-periodic")
        _execution_state["log_persist_task"] = _persist_task

        logger.info(f"Session started: {session['session_id']} mode={session['mode']} symbol={active_symbol}")

    elif action == "stop":
        # Set session status to idle IMMEDIATELY to prevent race conditions
        # (the _start_with_error_logging task checks this flag before saving to DB)
        session["status"] = "idle"
        
        # Force close any open position at market price
        pm = _execution_state["position_manager"]
        pos = pm.get_open()
        
        # TASK-1128 FIX: In live mode, also liquidate any untracked base asset balance.
        # Race condition: if the session is stopped between the market BUY and the bracket
        # registration, pm.get_open() returns None but we still hold the base asset.
        _stop_mode = _execution_state.get("session", {}).get("mode", "paper")
        _stop_exchange = _execution_state.get("exchange")
        if not pos and _stop_mode == "live" and _stop_exchange:
            active_sym = _execution_state.get("session", {}).get("symbol", "")
            if active_sym:
                try:
                    logger.info(f"[STOP] No tracked position but live mode — checking exchange balance for {active_sym} before stop")
                    await _handle_bracket_failed(_stop_exchange, active_sym.upper())
                except Exception as _stop_emergency_e:
                    logger.warning(f"[STOP] Emergency liquidation check failed (non-blocking): {_stop_emergency_e}")
        
        if pos:
            close_price: float = float(pos.entry_price)
            _mode_stop = _execution_state["session"].get("mode", "paper")
            exchange_stop = _execution_state.get("exchange")

            # Use latest candle price if available for more accurate close.
            # PAPER MODE: only use candle price if it's from the mock generator
            # (to avoid using real OKX prices for mock positions opened at ~100€).
            # LIVE MODE: always use latest candle.
            loop = _execution_state.get("loop")
            if loop and hasattr(loop, "_candle_buffer") and getattr(loop, "_candle_buffer", None):
                latest = loop._candle_buffer.latest
                if latest:
                    latest_price = float(latest.close)
                    if _mode_stop == "live":
                        close_price = latest_price
                    else:
                        # Paper: only use candle price if it's close to entry (within 10x)
                        # This avoids mixing real market prices with mock positions
                        if latest_price > 0 and abs(latest_price - float(pos.entry_price)) / float(pos.entry_price) < 9.0:
                            close_price = latest_price

            if _mode_stop == "live" and exchange_stop:
                # TASK-829: cancella OCO e attendi conferma prima di market sell
                try:
                    open_orders_before = await exchange_stop.get_open_orders(pos.symbol)
                    if open_orders_before:
                        ccxt_sym = await exchange_stop._get_ccxt_symbol(pos.symbol)
                        for o in open_orders_before:
                            try:
                                await exchange_stop.client.cancel_order(o["id"], ccxt_sym)
                            except Exception:
                                pass
                        logger.info(f"Cancellati {len(open_orders_before)} ordini OCO per stop sessione")

                        # Attendi conferma cancellazione (race condition protection)
                        await asyncio.sleep(0.5)
                        for _retry in range(3):
                            remaining = await exchange_stop.get_open_orders(pos.symbol)
                            if not remaining:
                                break
                            await asyncio.sleep(0.3)
                        else:
                            logger.warning(f"OCO orders still active after 3 retries for {pos.symbol}")
                except Exception as cancel_e:
                    logger.warning(f"OCO cancel on stop failed (non-blocking): {cancel_e}")

            # Close position at market
            try:
                await _close_position_and_record(pm, close_price, pos, reason="session_stop")
                logger.info(f"Position force-closed at market @ {close_price} due to session stop")
            except Exception as e:
                logger.error(f"Error force closing position during session stop: {e}", exc_info=True)
                if pos.status == "open" and _mode_stop != "live":
                    pm.close_position(Decimal(str(close_price)))
        
        # Stop WS client and pipeline
        asyncio.create_task(
            _stop_ws_broadcast(),
            name="scalping-ws-stop",
        )

        # Stop User Data Stream if active (TASK-827)
        uds = _execution_state.pop("user_data_stream", None)
        if uds:
            asyncio.create_task(uds.stop(), name="uds-stop")
        
        # Stop SupervisorScheduler if running
        if "supervisor_scheduler" in _execution_state and _execution_state["supervisor_scheduler"]:
            _execution_state["supervisor_scheduler"].stop()
            _execution_state["supervisor_scheduler"] = None
        
    # ── SESSION LOGGING: save log content to DB (deploy-safe) ──
        session_log_handler = _execution_state.pop("session_log_handler", None)
        mem_session_id = session.get("session_id")
        db_sid_for_log = session.get("db_session_id")
        log_symbol = session.get("symbol", "UNKNOWN")
        if session_log_handler and mem_session_id:
            try:
                log_content = session_log_handler.get_formatted_content(
                    session_id=mem_session_id,
                    symbol=log_symbol,
                )
                if log_content and db_sid_for_log:
                    supabase_log = get_supabase()
                    supabase_log.table("scalping_sessions").update({
                        "log_content": log_content,
                    }).eq("id", db_sid_for_log).execute()
                    logger.info(f"Session log content saved to DB for session {db_sid_for_log}")
            except Exception as log_e:
                logger.warning(f"Failed to save log content to DB: {log_e}")
        # Remove session log handler from root + forced loggers
        if session_log_handler:
            session_log_handler.detach()
        # Clear session_id from log context
        SessionContextFilter.set_session_id(None)

        # Clear session state
        session["session_id"] = None
        session["started_at"] = None
        session["stopped_at"] = _now()
        
        if _execution_state.get("exchange"):
            asyncio.create_task(_execution_state["exchange"].close(), name="close_exchange")
            _execution_state["exchange"] = None
        
        # Update DB: set status to "stopped"
        try:
            db_sid = session.get("db_session_id")
            if db_sid:
                supabase = get_supabase()
                # Calcola statistiche dalla trade history in memoria
                closed = [t for t in _execution_state.get("trade_history", []) if t.get("exit_price") is not None]
                total_pnl_val = round(sum((t.get("pnl") or 0) for t in closed), 4)
                win_count_val = len([t for t in closed if (t.get("pnl") or 0) > 0])
                supabase.table("scalping_sessions").update({
                    "status": "stopped",
                    "stopped_at": session["stopped_at"],
                    "trade_count": len(closed),
                    "win_count": win_count_val,
                    "total_pnl": total_pnl_val,
                }).eq("id", db_sid).execute()
                logger.info(f"Session {db_sid} stopped — trades={len(closed)} wins={win_count_val} pnl={total_pnl_val}")
        except Exception as e:
            logger.warning(f"Failed to update session in DB: {e}")
        
        logger.info(f"Session stopped — open positions closed at market")

    elif action == "pause":
        if session["status"] == "running":
            session["status"] = "paused"
            try:
                db_sid = session.get("db_session_id")
                if db_sid:
                    supabase = get_supabase()
                    supabase.table("scalping_sessions").update({
                        "status": "paused"
                    }).eq("id", db_sid).execute()
            except Exception as e:
                logger.warning(f"Failed to update session in DB: {e}")

    elif action == "resume":
        if session["status"] == "paused":
            # Se live mode, verifica prima che lo spot balance sia sufficiente
            if session.get("mode") == "live":
                try:
                    await _refresh_session_balance()
                    bal = session.get("live_balance", 0)
                    trade_val = float(session.get("trade_value", 10.0))
                    if bal is None or bal <= 0 or bal < trade_val:
                        logger.warning(
                            f"\033[91m⚠️ RESUME BLOCKED: Spot balance={bal} < trade_value={trade_val}. "
                            f"Still in Earn. Remain paused.\033[0m"
                        )
                        session["status"] = "paused"
                        return {"status": "paused", "reason": "spot_empty",
                                "message": "Ancora nessun fondo in Spot. Sposta fondi da Earn a Spot e riprova."}
                    logger.info(f"Resume: Spot balance OK ({bal}), resuming session.")
                except Exception as e:
                    logger.warning(f"Resume balance refresh failed (non-fatal): {e}")
                    # Se fallisce, resuma comunque — meglio di restare bloccati
            session["status"] = "running"
            try:
                db_sid = session.get("db_session_id")
                if db_sid:
                    supabase = get_supabase()
                    supabase.table("scalping_sessions").update({
                        "status": "running"
                    }).eq("id", db_sid).execute()
            except Exception as e:
                logger.warning(f"Failed to update session in DB: {e}")

    result = session.copy()
    try:
        result["signal_strength_threshold"] = get_scalping_config().signal_strength_threshold
    except Exception:
        result["signal_strength_threshold"] = None
    return result


# ---------------------------------------------------------------------------
# Session Log Download endpoint
# ---------------------------------------------------------------------------

from fastapi.responses import Response

@router.get("/session/{session_id}/logs")
async def download_session_logs(session_id: str) -> Response:
    """Download the log file for a given session.

    Genera il file .txt al volo dal contenuto salvato nel DB (log_content).
    I log vengono salvati nel DB allo stop della sessione.
    """
    try:
        supabase = get_supabase()
        resp = supabase.table("scalping_sessions") \
            .select("log_content, symbol") \
            .eq("id", session_id) \
            .limit(1) \
            .execute()

        if not resp.data:
            raise HTTPException(status_code=404, detail="Session not found.")

        row = resp.data[0]
        log_content = row.get("log_content")
        if not log_content:
            raise HTTPException(
                status_code=404,
                detail="Log non disponibili per questa sessione. "
                       "I log vengono salvati nel DB allo stop della sessione. "
                       "Sessioni precedenti alla migration potrebbero non averli."
            )

        symbol = row.get("symbol", "UNKNOWN")
        filename = f"session_{symbol}_{session_id}_logs.txt"
        return Response(
            content=log_content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to download session logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download logs: {e}")


@router.get("/session/{session_id}/logs/analysis")
async def get_session_log_analysis(session_id: str) -> Dict:
    """Restituisce l'analisi strutturata dei log di una sessione in formato JSON.

    Utile per analisi programmatiche e report automatici.
    Contiene conteggi e metriche estratte dai log raw.
    """
    try:
        supabase = get_supabase()
        resp = supabase.table("scalping_sessions") \
            .select("log_content, symbol") \
            .eq("id", session_id) \
            .limit(1) \
            .execute()

        if not resp.data:
            raise HTTPException(status_code=404, detail="Session not found.")

        row = resp.data[0]
        log_content = row.get("log_content")
        if not log_content:
            raise HTTPException(status_code=404, detail="Log non disponibili per questa sessione.")

        # Parse log lines back into a temporary handler for analysis
        from app.core.session_log_handler import SessionLogHandler

        # Create a temp handler and replay the log content through it
        temp_handler = SessionLogHandler()
        for line in log_content.split("\n"):
            if line.strip():
                # Skip header/footer lines
                if line.startswith("=") or line.startswith(" SESSION LOG DUMP") or \
                   line.startswith(" Session ID") or line.startswith(" Symbol") or \
                   line.startswith(" Entries") or line.startswith(" Generated") or \
                   line.startswith(" SESSION ANALYSIS SUMMARY"):
                    continue
                temp_handler._buffer.append(line)

        analysis = temp_handler.get_structured_analysis()

        # Convert Counter objects to dicts for JSON serialization
        def _clean(obj):
            if isinstance(obj, dict):
                return {k: _clean(v) for k, v in obj.items()}
            elif hasattr(obj, 'most_common'):
                return dict(obj)
            elif isinstance(obj, list):
                return [_clean(i) for i in obj]
            return obj

        return {
            "session_id": session_id,
            "symbol": row.get("symbol", "UNKNOWN"),
            "analysis": _clean(analysis),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to analyze session logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze logs: {e}")


# ---------------------------------------------------------------------------
# Position endpoints
# ---------------------------------------------------------------------------

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
            entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
            entry_commission = entry_val * entry_fee_rate
        
        # Exit: usa fee tier (costo di chiusura atteso al tier corrente)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO orders = maker
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
    entry_fee_rate = fee_tier.get("taker", 0.001)  # market order = taker
    exit_fee_rate = fee_tier.get("maker", 0.001)  # OCO orders = maker
    fee_round_trip = (entry_fee_rate + exit_fee_rate) * 100  # converti in percentuale
    
    # Calcola percentuali nette (sottrai fee round-trip dai target lordi)
    sl_pct_net = sl_pct - fee_round_trip  # perdita netta è peggiore
    tp_pct_net = tp_pct - fee_round_trip  # guadagno netto è minore

    # TASK-1129: veri prezzi TP/SL piazzati su OKX (fallback a ricalcolo da pct
    # per posizioni pre-fix / restore senza questi campi).
    _ef_p = fee_tier.get("taker", 0.001)
    _xf_p = fee_tier.get("maker", 0.001)
    # TASK-1127: Fees are now positive for base level accounts
    sl_price_calc = entry * (1 + _net_to_gross_pct(-sl_pct, _ef_p, _xf_p) / 100) if pos.side == "BUY" else entry * (1 - _net_to_gross_pct(-sl_pct, _ef_p, _xf_p) / 100)
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


# ---------------------------------------------------------------------------
# Runtime Config endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_scalping_config_endpoint():
    cfg = get_scalping_config()
    return {"config": cfg._config, "source": "env+db_override"}

@router.post("/config/reload")
async def reload_scalping_config():
    get_scalping_config().reload()
    return {"status": "reloaded"}

@router.post("/config/{key}")
async def update_scalping_config(key: str, value: str):
    db = get_supabase()
    db.table("scalping_runtime_config").update({
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("key", key).execute()
    get_scalping_config().reload()
    return {"key": key, "value": value, "status": "updated"}

# ---------------------------------------------------------------------------
# Risk Config endpoints
# ---------------------------------------------------------------------------

@router.get("/risk/config")
async def get_risk_config() -> Dict:
    try:
        supabase = get_supabase()
        response = supabase.table("scalping_risk_config").select("*").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            db_config = response.data[0]
            # Exclude id, updated_at from the active memory representation
            clean_config = {k: v for k, v in db_config.items() if k not in ["id", "updated_at"]}
            _execution_state["risk_config"] = clean_config
            return clean_config
    except Exception as e:
        logger.error(f"Error fetching risk config from DB: {e}")
    # Fallback to memory
    return _execution_state.get("risk_config", {})

@router.post("/risk/config")
async def update_risk_config(config: Dict) -> Dict:
    # Exclude position_size if present (managed via trade_value instead)
    clean_cfg = {k: v for k, v in config.items() if k != "position_size"}
    _execution_state["risk_config"] = clean_cfg
    
    # Persist to Supabase
    try:
        supabase = get_supabase()
        db_payload = {
            "id": 1,
            "max_daily_loss": clean_cfg.get("max_daily_loss", 50),
            "max_drawdown": clean_cfg.get("max_drawdown", 10),
            "leverage": clean_cfg.get("leverage", 10),
            "stop_loss_pct": clean_cfg.get("stop_loss_pct", 0.3),
            "take_profit_pct": clean_cfg.get("take_profit_pct", 0.5),
        }
        supabase.table("scalping_risk_config").upsert(db_payload).execute()
        logger.info("Persisted risk config to Supabase")
    except Exception as e:
        logger.error(f"Error persisting risk config to DB: {e}")
        
    return clean_cfg


@router.patch("/session/trade-value")
async def update_trade_value(body: Dict) -> Dict:
    """Update trade_value for the active session.
    
    This takes effect from the NEXT trade execution.
    Accepts: {"trade_value": <number>}
    """
    session = _execution_state["session"]
    try:
        new_value = max(1.0, float(body["trade_value"]))
        session["trade_value"] = new_value
        logger.info(f"Trade value updated to {new_value} USD (effective from next trade)")
        return {"trade_value": new_value, "status": session["status"]}
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid trade_value: {e}")

# ---------------------------------------------------------------------------
# Performance endpoint
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Diagnostic endpoint for pipeline debugging
# ---------------------------------------------------------------------------

@router.get("/debug/session-load")
async def debug_session_load():
    guard = _execution_state.get("session_load_guard")
    if not guard:
        return {"state": "no_guard"}
    return guard.monitor_data


@router.get("/debug/pipeline")
async def debug_pipeline():
    """Diagnostic endpoint to inspect pipeline state.
    
    Returns detailed state of:
    - CandleBuffer: size, ready status, latest candle
    - ExecutionLoop: buffer id, strategy, regime
    - Session: status, mode, symbol
    - WS client: connected status
    """
    loop = _execution_state.get("loop")
    buffer_info = {"size": 0, "ready": False, "latest": None}
    if loop and hasattr(loop, "_candle_buffer"):
        buf = loop._candle_buffer
        buffer_info = {
            "buffer_id": id(buf),
            "size": len(buf),
            "ready": buf.is_ready(),
            "latest_candle": {
                "close": float(buf.latest.close),
                "timestamp": str(buf.latest.timestamp),
            } if buf.latest else None,
        }

    strategy_name = loop.strategy.name if loop and loop.strategy else None
    regime_name = loop.regime.regime if loop and loop.regime else None

    ws_client = _execution_state.get("ws_client")
    ws_connected = ws_client is not None and not ws_client._stop_event.is_set() if ws_client else False

    return {
        "buffer": buffer_info,
        "execution_loop": {
            "strategy": strategy_name,
            "regime": regime_name,
            "running": loop.running if loop else False,
            "paper_mode": loop.paper_mode if loop else None,
        },
        "session": {
            "status": _execution_state["session"]["status"],
            "mode": _execution_state["session"]["mode"],
            "symbol": _execution_state["session"]["symbol"],
            "session_id": _execution_state["session"]["session_id"],
        },
        "ws_client": {
            "connected": ws_connected,
            "symbols": ws_client.symbols if ws_client else [],
        },
        "position_manager": {
            "has_open": _execution_state["position_manager"].has_open(),
            "total_trades": len(_execution_state["trade_history"]),
        },
    }


# ---------------------------------------------------------------------------
# Opportunity endpoints
# ---------------------------------------------------------------------------

# Opportunity scheduler singleton
_opportunity_scheduler: Optional[OpportunityScheduler] = None


async def _get_opportunity_scheduler() -> OpportunityScheduler:
    """Lazy init dello scheduler opportunity."""
    global _opportunity_scheduler
    if _opportunity_scheduler is None:
        _opportunity_scheduler = OpportunityScheduler()
        await _opportunity_scheduler.start(interval=60)
    return _opportunity_scheduler


@router.get("/opportunities")
async def get_opportunities(
    urgency: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get opportunities list with filters."""
    scheduler = await _get_opportunity_scheduler()

    # Convert string to enum
    urgency_enum = None
    if urgency:
        urgency_enum = OpportunityUrgency(urgency.upper())

    category_enum = None
    if category:
        category_enum = OpportunityCategory(category.lower())

    opportunities = scheduler.router.get_opportunities(
        urgency=urgency_enum,
        category=category_enum,
        limit=limit,
    )

    result = [
        {
            "id": opp.id,
            "symbol": opp.symbol,
            "category": opp.category.value,
            "urgency": opp.urgency.value,
            "source": opp.source.value,
            "title": opp.title,
            "description": opp.description,
            "url": opp.url,
            "is_tradeable": opp.is_tradeable,
            "confidence_score": opp.confidence_score,
            "published_at": opp.published_at.isoformat() if opp.published_at else None,
            "created_at": opp.created_at.isoformat(),
            "is_watched": opp.is_watched,
            "is_ignored": opp.is_ignored,
        }
        for opp in opportunities
    ]
    
    logger.info(
        f"GET /opportunities: {len(result)} opportunities returned "
        f"(filter urgency={urgency})"
    )
    
    return result


@router.post("/opportunities/{opportunity_id}/watchlist")
async def add_to_watchlist(opportunity_id: str) -> Dict:
    """Aggiunge simbolo a watchlist engine."""
    scheduler = await _get_opportunity_scheduler()

    for opp in scheduler.router._opportunities:
        if opp.id == opportunity_id and opp.symbol:
            if opp.symbol not in scheduler.router._watchlist:
                scheduler.router._watchlist.append(opp.symbol)
            opp.is_watched = True
            return {"status": "added", "symbol": opp.symbol}

    raise HTTPException(status_code=404, detail="Opportunity not found")


@router.post("/opportunities/{opportunity_id}/ignore")
async def ignore_opportunity(opportunity_id: str) -> Dict:
    """Marca un'opportunità come ignorata."""
    scheduler = await _get_opportunity_scheduler()

    if scheduler.router.mark_ignored(opportunity_id):
        return {"status": "ignored"}

    raise HTTPException(status_code=404, detail="Opportunity not found")


@router.get("/opportunities/watchlist")
async def get_opportunity_watchlist() -> List[str]:
    """Recupera la watchlist simboli."""
    scheduler = await _get_opportunity_scheduler()
    return scheduler.router.get_watchlist()


# ---------------------------------------------------------------------------
# TASK-911: Supervisor history endpoint
# ---------------------------------------------------------------------------
@router.get("/supervisor/history")
async def get_supervisor_history(session_id: str, limit: int = 50) -> List[Dict]:
    """Recupera le decisioni del supervisor per una sessione specifica.

    Accetta sia il session_id interno (sess_XXXXXXXX) sia il db_session_id (UUID).
    Se viene passato il session_id interno, viene tradotto al db_session_id via
    _execution_state per evitare l'errore 22P02 sul DB.
    """
    try:
        # Translate in-memory session_id -> db_session_id if needed
        db_sid = session_id
        cur = _execution_state.get("session", {})
        if cur.get("session_id") == session_id and cur.get("db_session_id"):
            db_sid = cur["db_session_id"]

        if not db_sid or db_sid == session_id and not _is_valid_uuid(db_sid):
            # No DB session yet (DB insert may have failed) — return empty list silently
            return []

        supabase = get_supabase()

        def _fetch():
            resp = supabase.table("supervisor_memory") \
                .select("*") \
                .eq("session_id", db_sid) \
                .order("decided_at", desc=True) \
                .limit(limit) \
                .execute()
            return resp.data if resp.data else []

        records = await asyncio.to_thread(_fetch)

        # Normalizza i campi per il frontend
        result = []
        for r in records:
            entry = {
                "action": r.get("action", "no_action"),
                "reason": r.get("reason", ""),
                "confidence": r.get("confidence", 0.0),
                "timestamp": r.get("decided_at"),
                "decided_at": r.get("decided_at"),
                "market_bias": r.get("market_bias"),
                "primary_signal": r.get("primary_signal"),
                "new_strategy": r.get("new_strategy"),
                "new_params": r.get("new_params"),
                "was_applied": r.get("was_applied", True),
                "blocked_reason": r.get("blocked_reason"),
            }
            result.append(entry)

        logger.info(
            f"GET /supervisor/history: {len(result)} records for session_id={session_id[:8]}..."
        )
        return result

    except Exception as e:
        logger.error(f"GET /supervisor/history error: {e}")
        return []
