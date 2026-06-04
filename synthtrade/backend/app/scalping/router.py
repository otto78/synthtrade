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
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

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
from app.scalping.engine.ws_client import BinanceWSClient, CandleEvent, TradeEvent
from app.db.supabase_client import get_supabase
from app.scalping.data.candle_buffer import CandleBuffer
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.engine.signal_aggregator import SignalAggregator
from app.scalping.engine.regime_detector import RegimeDetector
from app.scalping.engine.strategy_selector import StrategySelector
from app.scalping.models.market import Candle
from app.execution.exchange import BinanceExchangeAdapter
from app.config import settings

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
    "ws_client": None,          # BinanceWSClient instance
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
    }
}

# WebSocket connections
_scalping_ws_connections: List[WebSocket] = []

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

    try:
        # DON'T send initial session state — it would overwrite any running state
        # that the user just set via POST /api/scalping/session.
        # Session state is read by the client via GET /api/scalping/session when needed.

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Helper: wire BinanceWSClient events → broadcast to scalping WS clients
# ---------------------------------------------------------------------------

async def _close_position_and_record(pm, close_price: float, pos, reason: str = "signal"):
    """Helper to close position, deduct fees, calculate PnL and record trade."""
    qty = float(pos.quantity)
    
    # --- LIVE EXECUTION OVERRIDE ---
    mode = _execution_state["session"].get("mode", "paper")
    exchange = _execution_state.get("exchange")
    real_fees = None
    
    if mode == "live" and exchange:
        try:
            # 1. Cancel OCO / Stop Loss orders
            if getattr(pos, "oco_id", None) or getattr(pos, "sl_id", None):
                await exchange.client.cancel_all_orders(pos.symbol)
                logger.info(f"Cancelled open OCO/SL orders for {pos.symbol}")
            
            # 2. Execute Market Close
            opp_side = "sell" if pos.side.upper() == "BUY" else "buy"
            market_res = await exchange.place_market_order(pos.symbol, opp_side, qty)
            
            # 3. Use real execution price
            if market_res.get("price"):
                close_price = float(market_res["price"])
            logger.info(f"LIVE Market Close executed @ {close_price}")
        except Exception as e:
            logger.error(f"Failed to close live position for {pos.symbol}: {e}")
    # -------------------------------
    
    entry_val = float(pos.entry_price) * qty
    exit_val = close_price * qty
    gross_pnl = (close_price - float(pos.entry_price)) * qty * (1 if pos.side == "BUY" else -1)
    fees = (entry_val * 0.001) + (exit_val * 0.001)  # 0.1% entry + 0.1% exit
    pnl = gross_pnl - fees
    pnl_pct = (pnl / entry_val) * 100
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
    }
    _execution_state["trade_history"].append(trade_record)
    await broadcast_scalping_event("trade_closed", trade_record)
    logger.info(f"Position closed ({reason}): {pos.side} {pos.symbol} PnL: {pnl:.2f} ({pnl_pct:.2f}%)")
    
    # Save trade to Supabase
    try:
        db_sid = _execution_state["session"].get("db_session_id")
        if db_sid:
            supabase = get_supabase()
            supabase.table("scalping_trades").insert({
                "session_id": db_sid,
                "symbol": trade_record["symbol"],
                "side": trade_record["side"],
                "entry_price": trade_record["entry_price"],
                "exit_price": trade_record["exit_price"],
                "quantity": trade_record["quantity"],
                "pnl": trade_record["pnl"],
                "pnl_pct": trade_record["pnl_pct"],
                "strategy_type": _execution_state["session"].get("strategy", "unknown"),
                "signal_reason": reason,
                "status": "closed",
                "entry_time": pos.entry_time.isoformat(),
                "exit_time": trade_record["timestamp"]
            }).execute()
    except Exception as db_e:
        logger.warning(f"Failed to insert trade in DB: {db_e}")

def _check_daily_loss() -> bool:
    """Return True if max daily loss is exceeded."""
    risk_cfg = _execution_state.get("risk_config", {})
    max_loss = float(risk_cfg.get("max_daily_loss", 50.0))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_pnl = sum(t["pnl"] for t in _execution_state["trade_history"] if t["timestamp"].startswith(now_str))
    return total_pnl <= -max_loss

async def _start_ws_broadcast(symbol: str):
    """Create BinanceWSClient, connect to Binance, and broadcast candle/trade events
    to all connected scalping WS clients.
    
    Also feeds the CandleBuffer and ExecutionLoop pipelines for signal generation.
    """
    is_testnet = _execution_state["session"].get("mode") != "live"
    client = BinanceWSClient(symbols=[symbol], testnet=is_testnet)
    _execution_state["ws_client"] = client
    await client.start()

    # Create pipeline components
    candle_buffer = CandleBuffer()
    signal_engine = _execution_state.get("signal_engine")
    if not signal_engine:
        signal_engine = SignalScoreEngine(symbol=symbol)
        _execution_state["signal_engine"] = signal_engine
    
    execution_loop = ExecutionLoop(
        symbol=symbol,
        candle_buffer=candle_buffer,
        signal_engine=signal_engine,
        signal_aggregator=SignalAggregator(),
        regime_detector=RegimeDetector(),
        strategy_selector=StrategySelector(),
        position_manager=_execution_state["position_manager"],
    )
    _execution_state["loop"] = execution_loop

    # Warm up the candle buffer with historical candles so indicators are immediately ready
    # and broadcast them to the frontend so the chart is populated immediately
    try:
        from app.scalping.backtest.historical_loader import HistoricalLoader
        loader = HistoricalLoader()
        logger.info(f"Pre-loading past 100 1m candles for {symbol.upper()} to warm up buffer...")
        past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
        if past_candles:
            for c in past_candles:
                candle_buffer.add(c)
                # Broadcast each historical candle to frontend WS clients
                await broadcast_scalping_event("candle", {
                    "symbol": symbol,
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close),
                    "volume": float(c.volume),
                    "timestamp": c.timestamp.isoformat(),
                })
            logger.info(f"Successfully loaded and broadcast {len(past_candles)} historical candles for {symbol}. Buffer ready: {candle_buffer.is_ready(50)}")
        else:
            logger.warning(f"No historical candles returned for {symbol}, buffer will warm up live.")
    except Exception as warmup_err:
        logger.warning(f"Could not warm up candle buffer with historical data: {warmup_err}")

    # Mock data generator that creates synthetic candles when no real WS data arrives
    _mock_candle_counter = 0
    _mock_last_price = None

    # Symbol-appropriate base prices for mock data
    _SYMBOL_BASE_PRICES = {
        "BTCUSDT": 65000.0,
        "ETHUSDT": 3500.0,
        "BNBUSDT": 600.0,
        "SOLUSDT": 150.0,
        "ADAUSDT": 0.45,
        "XRPUSDT": 0.50,
        "DOTUSDT": 7.0,
        "DOGEUSDT": 0.12,
        "AVAXUSDT": 35.0,
        "MATICUSDT": 0.55,
    }

    async def _mock_candle_generator():
        """Generate synthetic candles every 5 seconds as fallback when no Binance WS data."""
        nonlocal _mock_candle_counter, _mock_last_price
        base_price = _SYMBOL_BASE_PRICES.get(symbol.upper(), 100.0)  # Fallback 100 for unknown symbols
        _mock_last_price = base_price
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            await asyncio.sleep(4.0)
            if _execution_state["session"]["status"] != "running":
                continue
            _mock_candle_counter += 1
            # Random-ish price movement proportional to price
            import random
            movement_pct = (random.random() - 0.48) * 0.003  # ±0.15% per tick with slight bullish bias
            movement = movement_pct * base_price
            close_price = _mock_last_price + movement
            high_price = max(close_price, _mock_last_price) + abs(movement) * 0.5
            low_price = min(close_price, _mock_last_price) - abs(movement) * 0.5
            _mock_last_price = close_price
            now_ts = datetime.now(timezone.utc)
            
            # Build a mock CandleEvent-like dict
            candle_data = {
                "symbol": symbol,
                "open": round(_mock_last_price - movement, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": round(random.random() * 100 + 50, 4),
                "timestamp": now_ts.isoformat(),
                "is_closed": True,
            }
            
            await broadcast_scalping_event("candle", candle_data)
            
            # Update PnL and check SL/TP on every candle if there's an open position
            pm = _execution_state["position_manager"]
            pos = pm.get_open()
            if pos:
                entry_f = float(pos.entry_price)
                current_f = close_price
                qty_f = float(pos.quantity)
                entry_val = entry_f * qty_f
                current_val = current_f * qty_f
                gross_pnl = (current_f - entry_f) * qty_f if pos.side == "BUY" else (entry_f - current_f) * qty_f
                fees = (entry_val * 0.001) + (current_val * 0.001)
                pnl = gross_pnl - fees
                pnl_pct = (pnl / entry_val) * 100
                
                # Check SL/TP
                risk_cfg = _execution_state.get("risk_config", {})
                sl_pct = float(risk_cfg.get("stop_loss_pct", 0.3)) / 100
                tp_pct = float(risk_cfg.get("take_profit_pct", 0.5)) / 100
                sl = entry_f * (1 - sl_pct) if pos.side == "BUY" else entry_f * (1 + sl_pct)
                tp = entry_f * (1 + tp_pct) if pos.side == "BUY" else entry_f * (1 - tp_pct)
                
                await broadcast_scalping_event("position_update", {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": entry_f,
                    "current_price": current_f,
                    "quantity": qty_f,
                    "pnl": round(pnl, 4),
                    "pnl_pct": round(pnl_pct, 4),
                    "stop_loss_price": round(sl, 2),
                    "take_profit_price": round(tp, 2),
                })
                
                # Execute SL/TP Auto Close
                hit_sl = (pos.side == "BUY" and current_f <= sl) or (pos.side == "SELL" and current_f >= sl)
                hit_tp = (pos.side == "BUY" and current_f >= tp) or (pos.side == "SELL" and current_f <= tp)
                if hit_sl:
                    await _close_position_and_record(pm, current_f, pos, reason="stop_loss")
                    continue
                elif hit_tp:
                    await _close_position_and_record(pm, current_f, pos, reason="take_profit")
                    continue

            logger.debug(f"Mock candle #{_mock_candle_counter}: {candle_data['close']}")

            # Generate a mock signal every ~4 candles (20 seconds)
            if _mock_candle_counter % 4 == 0:
                side = "BUY" if random.random() > 0.4 else "SELL"
                conf = round(random.random() * 0.3 + 0.5, 2)  # 0.5-0.8
                await broadcast_scalping_event("signal", {
                    "symbol": symbol.upper(),
                    "type": side,
                    "price": close_price,
                    "confidence": conf,
                    "reason": f"Mock {side} signal (simulated)",
                })
                logger.info(f"Mock signal: {side} {symbol.upper()} @ {close_price:.2f}")

                # Open/close paper trades
                pm = _execution_state["position_manager"]
                risk_cfg = _execution_state.get("risk_config", {})
                trade_value_usd = float(_execution_state["session"].get("trade_value", 100.0))
                sl_pct = float(risk_cfg.get("stop_loss_pct", 0.3)) / 100
                tp_pct = float(risk_cfg.get("take_profit_pct", 0.5)) / 100
                
                if not pm.has_open():
                    if _check_daily_loss():
                        logger.warning("Max daily loss exceeded. Blocking new mock trade.")
                        continue
                        
                    quantity = Decimal(str(round(trade_value_usd / close_price, 6)))
                    pos_obj = pm.open_position(
                        symbol=symbol.upper(),
                        side=side,
                        entry_price=Decimal(str(close_price)),
                        quantity=quantity,
                    )
                    sl_price = round(float(pos_obj.entry_price) * (1 - sl_pct), 2) if side == "BUY" else round(float(pos_obj.entry_price) * (1 + sl_pct), 2)
                    tp_price = round(float(pos_obj.entry_price) * (1 + tp_pct), 2) if side == "BUY" else round(float(pos_obj.entry_price) * (1 - tp_pct), 2)
                    await broadcast_scalping_event("position", {
                        "symbol": pos_obj.symbol,
                        "side": pos_obj.side,
                        "entry_price": float(pos_obj.entry_price),
                        "current_price": float(close_price),
                        "quantity": float(pos_obj.quantity),
                        "pnl": 0.0,
                        "pnl_pct": 0.0,
                        "stop_loss_price": sl_price,
                        "take_profit_price": tp_price,
                        "stop_loss_pct": float(risk_cfg.get("stop_loss_pct", 0.3)),
                        "take_profit_pct": float(risk_cfg.get("take_profit_pct", 0.5)),
                    })
                    logger.info(f"Mock paper trade opened: {side} {symbol.upper()} @ {close_price:.2f}")
                else:
                    # Close existing position and record trade
                    pos = pm.get_open()
                    if pos.side != side:
                        await _close_position_and_record(pm, close_price, pos, reason="reverse_signal")

    # Pull events from BinanceWSClient queues and broadcast to scalping WS clients
    async def _candle_processor():
        """Consume candle_queue and broadcast + feed execution loop."""
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            try:
                event = await asyncio.wait_for(client.candle_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if _execution_state["session"]["status"] == "idle":
                    break
                continue

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

            # Feed into execution loop for signal generation (only closed candles)
            if event.is_closed and _execution_state["session"]["status"] == "running":
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
                try:
                    decision = await execution_loop.process_candle(candle)
                    if decision and decision.execute:
                        # A signal was generated — broadcast it
                        await broadcast_scalping_event("signal", {
                            "symbol": event.symbol.upper(),
                            "type": "BUY" if decision.confidence > 0 else "SELL",
                            "price": float(candle.close),
                            "confidence": abs(decision.confidence),
                            "reason": decision.reason,
                        })

                        # Simulate trade execution for paper mode
                        pm = _execution_state["position_manager"]
                        side = "BUY" if decision.confidence > 0 else "SELL"
                        if not pm.has_open():
                            if _check_daily_loss():
                                logger.warning("Max daily loss exceeded. Blocking new real trade.")
                                continue
                                
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
                                    _qty_raw = _trade_val / float(event.close)
                                    step_size = float(filters["stepSize"])
                                    _qty_precise = round(_qty_raw - (_qty_raw % step_size), 8)
                                    
                                    if _qty_precise < float(filters["minQty"]):
                                        logger.error(f"Quantity too small: {_qty_precise} < {filters['minQty']}")
                                        continue
                                        
                                    # 3. Execute Market Order
                                    market_res = await exchange.place_market_order(event.symbol.upper(), side, _qty_precise)
                                    exec_price = float(market_res.get("price") or event.close)
                                    exec_qty = float(market_res.get("quantity") or _qty_precise)
                                    
                                    # 4. Calculate Risk SL/TP with proper price precision
                                    risk_cfg = _execution_state.get("risk_config", {})
                                    sl_pct = float(risk_cfg.get("stop_loss_pct", 0.3)) / 100
                                    tp_pct = float(risk_cfg.get("take_profit_pct", 0.5)) / 100
                                    price_prec = int(filters.get("pricePrecision", 2))
                                    
                                    sl_price = round(exec_price * (1 - sl_pct), price_prec) if side == "BUY" else round(exec_price * (1 + sl_pct), price_prec)
                                    tp_price = round(exec_price * (1 + tp_pct), price_prec) if side == "BUY" else round(exec_price * (1 - tp_pct), price_prec)
                                    
                                    # 5. Place OCO Risk Parachute
                                    oco_res = await exchange.place_oco_order(
                                        symbol=event.symbol.upper(),
                                        side="SELL" if side == "BUY" else "BUY",
                                        quantity=exec_qty,
                                        price=tp_price,
                                        stop_price=sl_price,
                                        take_profit_price=tp_price
                                    )
                                    
                                    # 6. Store locally for PnL tracking
                                    pos_obj = pm.open_position(
                                        symbol=event.symbol.upper(),
                                        side=side,
                                        entry_price=Decimal(str(exec_price)),
                                        quantity=Decimal(str(exec_qty))
                                    )
                                    pos_obj.oco_id = oco_res.get("order_id")
                                    pos_obj.sl_id = oco_res.get("stop_loss_id")
                                    pos_obj.tp_id = oco_res.get("take_profit_id")
                                    
                                    await broadcast_scalping_event("position", {
                                        "symbol": pos_obj.symbol,
                                        "side": pos_obj.side,
                                        "entry_price": float(pos_obj.entry_price),
                                        "current_price": float(candle.close),
                                        "quantity": float(pos_obj.quantity),
                                        "pnl": 0.0,
                                        "pnl_pct": 0.0,
                                    })
                                    logger.info(f"LIVE trade opened: {side} {event.symbol.upper()} @ {exec_price}")
                                    
                                except Exception as live_e:
                                    logger.error(f"Live trade failed: {live_e}")
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
                                await broadcast_scalping_event("position", {
                                    "symbol": pos_obj.symbol,
                                    "side": pos_obj.side,
                                    "entry_price": float(pos_obj.entry_price),
                                    "current_price": float(candle.close),
                                    "quantity": float(pos_obj.quantity),
                                    "pnl": 0.0,
                                    "pnl_pct": 0.0,
                                })
                                logger.info(f"Paper trade opened: {side} {event.symbol.upper()} @ {candle.close}")
                        else:
                            # If opposite signal, close position
                            pos = pm.get_open()
                            if pos.side != side:
                                await _close_position_and_record(pm, float(candle.close), pos, reason=decision.reason or "signal")
                except Exception as e:
                    logger.warning(f"Execution loop processing error: {e}")

    async def _trade_processor():
        """Consume trade_queue and broadcast + update PnL."""
        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():
            try:
                event = await asyncio.wait_for(client.trade_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if _execution_state["session"]["status"] == "idle":
                    break
                continue

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
                sl_pct = float(risk_cfg.get("stop_loss_pct", 0.3)) / 100
                tp_pct = float(risk_cfg.get("take_profit_pct", 0.5)) / 100
                sl = entry * (1 - sl_pct) if pos.side == "BUY" else entry * (1 + sl_pct)
                tp = entry * (1 + tp_pct) if pos.side == "BUY" else entry * (1 - tp_pct)
                
                gross_pnl = (current - entry) * qty if pos.side == "BUY" else (entry - current) * qty
                fees = (entry_val * 0.001) + (current_val * 0.001)
                pnl = gross_pnl - fees
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
                
                # Execute SL/TP Auto Close
                hit_sl = (pos.side == "BUY" and current <= sl) or (pos.side == "SELL" and current >= sl)
                hit_tp = (pos.side == "BUY" and current >= tp) or (pos.side == "SELL" and current <= tp)
                if hit_sl:
                    await _close_position_and_record(pm, current, pos, reason="stop_loss")
                elif hit_tp:
                    await _close_position_and_record(pm, current, pos, reason="take_profit")

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
                    except Exception as db_e:
                        logger.warning(f"Failed to insert intelligence in DB: {db_e}")

                except Exception as e:
                    logger.warning(f"Intelligence broadcast error: {e}")
            await asyncio.sleep(10.0)

    # Start processor tasks + mock generator fallback for testnet
    task_candle = asyncio.create_task(_candle_processor(), name=f"candle-proc-{symbol}")
    task_trade = asyncio.create_task(_trade_processor(), name=f"trade-proc-{symbol}")
    task_mock = asyncio.create_task(_mock_candle_generator(), name=f"mock-candle-{symbol}")
    task_intel = asyncio.create_task(_intelligence_processor(), name=f"intel-proc-{symbol}")
    _execution_state["ws_tasks"] = [task_candle, task_trade, task_mock, task_intel]
    logger.info(f"Mock data generator started for {symbol} (fallback when Binance WS unavailable)")

    # Log how many frontend WS clients are connected
    ws_count = len(_scalping_ws_connections)
    logger.info(f"Scalping broadcast started for {symbol} — {ws_count} frontend WS client(s) connected")
    logger.info(f"Mock data generator enabled (real Binance WS may be unavailable or slow)")


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


@router.get("/trade-history")
async def get_trade_history(limit: int = 50) -> List[Dict]:
    """Get trade history from the current session."""
    return _execution_state["trade_history"][-limit:]


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, limit: int = 100) -> List[Dict]:
    """Get candle history for a symbol.

    1. Tries the ExecutionLoop's candle buffer first (fast, already loaded).
    2. Falls back to Binance REST API if buffer is empty (e.g. warmup still in progress).

    Used by the frontend to load historical candles when a session starts.
    """
    # Strategy 1: try the in-memory candle buffer
    loop = _execution_state.get("loop")
    if loop and hasattr(loop, "_candle_buffer"):
        try:
            candles = loop._candle_buffer.get()
            if candles:
                result = []
                for c in candles:
                    if c.symbol.upper() != symbol.upper():
                        continue
                    result.append({
                        "symbol": symbol,
                        "open": float(c.open),
                        "high": float(c.high),
                        "low": float(c.low),
                        "close": float(c.close),
                        "volume": float(c.volume),
                        "timestamp": c.timestamp.isoformat(),
                    })
                    if len(result) >= limit:
                        break
                if result:
                    logger.info(f"Returning {len(result)} candles from buffer for {symbol}")
                    return result
        except Exception as e:
            logger.warning(f"Buffer read failed for {symbol}: {e}")

    # Strategy 2: fallback to Binance REST API
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
            logger.info(f"Returning {len(result)} candles from Binance REST for {symbol}")
            return result
    except Exception as e:
        logger.warning(f"Binance REST fallback failed for {symbol}: {e}")

    return []


async def _stop_ws_broadcast():
    """Stop BinanceWSClient and clean up pipeline components."""
    client = _execution_state.get("ws_client")
    if client:
        await client.stop()
        _execution_state["ws_client"] = None
    
    loop = _execution_state.get("loop")
    if loop:
        await loop.stop()
        _execution_state["loop"] = None
    
    _execution_state["signal_engine"] = None

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

@router.get("/session")
async def get_session() -> Dict:
    """Get current session status."""
    return _execution_state["session"].copy()


@router.post("/session")
async def control_session(control: Dict) -> Dict:
    """Control session: start, stop, pause, resume."""
    session = _execution_state["session"]
    action = control.get("action")

    if action == "start":
        active_symbol = control.get("symbol", session.get("symbol", "BTCUSDT"))
        session["status"] = "running"
        session["session_id"] = f"sess_{uuid.uuid4().hex[:8]}"
        session["mode"] = control.get("mode", session.get("mode", "paper"))
        session["strategy"] = control.get("strategy", "scalping_v2")
        session["symbol"] = active_symbol
        session["trade_value"] = float(control.get("trade_value", session.get("trade_value", 10.0)))
        session["started_at"] = _now()
        session["stopped_at"] = None
        
        # Reset trade history and position manager for the new session
        _execution_state["trade_history"] = []
        _execution_state["position_manager"] = PositionManager()
        _execution_state["exchange"] = None
        
        if session["mode"] == "live":
            api_key = settings.BINANCE_API_KEY_LIVE or settings.BINANCE_API_KEY
            api_secret = settings.BINANCE_SECRET_KEY_LIVE or settings.BINANCE_SECRET_KEY
            if not api_key or not api_secret:
                raise HTTPException(status_code=400, detail="Mancano le API Key nel file .env per la modalità Live.")
            # Scalping live → always real Binance, never testnet
            _execution_state["exchange"] = BinanceExchangeAdapter(api_key, api_secret, testnet=False)
            logger.info("BinanceExchangeAdapter initialized for LIVE execution (testnet=False).")
        
        # Store trade_value from UI (USD amount per trade)
        if "trade_value" in control:
            try:
                session["trade_value"] = max(1.0, float(control["trade_value"]))
            except (TypeError, ValueError):
                pass  # keep existing value

        # Initialize SignalScoreEngine for the symbol
        try:
            _execution_state["signal_engine"] = SignalScoreEngine(symbol=active_symbol)
        except Exception as e:
            logger.warning(f"Could not initialize SignalScoreEngine: {e}")

        # Start BinanceWSClient + ExecutionLoop pipeline
        async def _start_with_error_logging():
            """Wrapper that logs any exception from _start_ws_broadcast."""
            try:
                await _start_ws_broadcast(active_symbol.lower())
                
                # Save to Supabase after successful start
                try:
                    supabase = get_supabase()
                    db_resp = supabase.table("scalping_sessions").insert({
                        "symbol": session["symbol"],
                        "mode": session["mode"].upper(),
                        "timeframe": "1m",
                        "status": "running",
                        "started_at": session["started_at"]
                    }).execute()
                    if db_resp.data:
                        session["db_session_id"] = db_resp.data[0]["id"]
                        logger.info(f"Session saved to DB with id={session['db_session_id']}")
                except Exception as db_e:
                    logger.warning(f"Failed to insert session in DB: {db_e}")
                    
                # Start SupervisorScheduler (every 45s for live debugging/monitoring)
                from app.scalping.supervisor.supervisor_scheduler import SupervisorScheduler
                supervisor = SupervisorScheduler(symbol=active_symbol, interval_seconds=45)
                # Attach db_session_id (UUID) so the supervisor can log it to DB
                _execution_state["loop"].session_id = session.get("db_session_id")
                supervisor.set_execution_loop(_execution_state["loop"])
                supervisor.start()
                _execution_state["supervisor_scheduler"] = supervisor
                    
            except Exception as e:
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
        
        logger.info(f"Session started: {session['session_id']} mode={session['mode']} symbol={active_symbol}")

    elif action == "stop":
        # Force close open position if any
        pm = _execution_state["position_manager"]
        pos = pm.get_open()
        if pos:
            # Initialise close_price with a safe fallback (entry price) to guarantee the variable is bound
            close_price: float = float(pos.entry_price)
            try:
                # Attempt to use the latest candle price if available
                loop = _execution_state.get("loop")
                if loop and hasattr(loop, "_candle_buffer") and getattr(loop, "_candle_buffer", None):
                    latest = loop._candle_buffer.latest
                    if latest:
                        close_price = float(latest.close)
                await _close_position_and_record(pm, close_price, pos, reason="session_stop")
            except Exception as e:
                logger.error(f"Error force closing position during session stop: {e}", exc_info=True)
            finally:
                # Guarantee local state reflects position closure – only attempt if we still have an open position
                if pos.status == "open":
                    pm.close_position(Decimal(str(close_price)))
            
        # Stop BinanceWSClient and pipeline
        asyncio.create_task(
            _stop_ws_broadcast(),
            name="scalping-ws-stop",
        )
        
        # Stop SupervisorScheduler if running
        if "supervisor_scheduler" in _execution_state and _execution_state["supervisor_scheduler"]:
            _execution_state["supervisor_scheduler"].stop()
            _execution_state["supervisor_scheduler"] = None
            
        session["status"] = "idle"
        session["session_id"] = None
        session["started_at"] = None
        session["stopped_at"] = _now()
        
        if _execution_state.get("exchange"):
            # We don't await the close here as it might block, or we can launch a task
            asyncio.create_task(_execution_state["exchange"].close(), name="close_exchange")
            _execution_state["exchange"] = None
        
        # Update DB
        try:
            db_sid = _execution_state["session"].get("db_session_id")
            if db_sid:
                supabase = get_supabase()
                supabase.table("scalping_sessions").update({
                    "status": "stopped",
                    "stopped_at": session["stopped_at"]
                }).eq("id", db_sid).execute()
        except Exception as e:
            logger.warning(f"Failed to update session in DB: {e}")

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

    return session.copy()


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
    loop = _execution_state.get("loop")
    if loop and hasattr(loop, "_candle_buffer") and len(loop._candle_buffer) > 0:
        candles = loop._candle_buffer.get()
        current_price = float(candles[-1].close)
        qty = float(pos.quantity)
        entry = float(pos.entry_price)
        entry_val = entry * qty
        current_val = current_price * qty
        gross_pnl = (current_price - entry) * qty if pos.side == "BUY" else (entry - current_price) * qty
        fees = (entry_val * 0.001) + (current_val * 0.001)
        pnl = gross_pnl - fees
        pnl_pct = (pnl / entry_val) * 100
    else:
        current_price = float(pos.entry_price)
        pnl = 0.0
        pnl_pct = 0.0
    
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
    trades = _execution_state["trade_history"]
    
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
    
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    losing = [t for t in trades if t.get("pnl", 0) < 0]
    
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    win_count = len(winning)
    lose_count = len(losing)
    total = len(trades)
    
    avg_win = sum(t.get("pnl", 0) for t in winning) / win_count if win_count else 0
    avg_loss = abs(sum(t.get("pnl", 0) for t in losing) / lose_count) if lose_count else 0
    
    gross_profit = sum(t.get("pnl", 0) for t in winning)
    gross_loss = abs(sum(t.get("pnl", 0) for t in losing))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else 0
    
    # Calculate max drawdown from running equity
    running_pnl = 0
    base_balance = float(_execution_state["session"].get("paper_balance", 10000.0))
    equity = base_balance
    peak_equity = base_balance
    max_dd_pct = 0.0
    for t in trades:
        running_pnl += t.get("pnl", 0)
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
        if t.get("pnl", 0) < 0:
            cons_losses += 1
        else:
            break
    # Also calculate historical max consecutive losses
    current_run = 0
    for t in trades:
        if t.get("pnl", 0) < 0:
            current_run += 1
            max_cons_losses = max(max_cons_losses, current_run)
        else:
            current_run = 0
    
    initial_balance = _execution_state["session"].get("paper_balance", 10000.0)
    total_pnl_pct = (total_pnl / initial_balance) * 100 if initial_balance else 0

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
    for opp in result:
        logger.info(
            f"  opp: [{opp['urgency']}] {opp['title']} "
            f"({opp['symbol']}) - {opp['source']}"
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