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
from app.scalping.data.candle_buffer import CandleBuffer
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.engine.signal_aggregator import SignalAggregator
from app.scalping.engine.regime_detector import RegimeDetector
from app.scalping.engine.strategy_selector import StrategySelector
from app.scalping.models.market import Candle

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
    },
    "trade_history": [],        # List[dict] — trade history for performance calc
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
        # Send initial state
        state = _execution_state["session"]
        await ws.send_json({"type": "session", "payload": state, "timestamp": _now()})

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

async def _start_ws_broadcast(symbol: str):
    """Create BinanceWSClient, connect to Binance, and broadcast candle/trade events
    to all connected scalping WS clients.
    
    Also feeds the CandleBuffer and ExecutionLoop pipelines for signal generation.
    """
    client = BinanceWSClient(symbols=[symbol])
    _execution_state["ws_client"] = client

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
                        if not pm.has_open():
                            side = "BUY" if decision.confidence > 0 else "SELL"
                            pos_obj = pm.open_position(
                                symbol=event.symbol.upper(),
                                side=side,
                                entry_price=Decimal(str(event.close)),
                                quantity=Decimal("0.001"),  # minimal paper quantity
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
                if pos.side == "BUY":
                    pnl = (current - entry) * qty
                    pnl_pct = (current - entry) / entry * 100
                else:
                    pnl = (entry - current) * qty
                    pnl_pct = (entry - current) / entry * 100
                await broadcast_scalping_event("position_update", {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": entry,
                    "current_price": current,
                    "quantity": qty,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                })

    # Start processor tasks
    task_candle = asyncio.create_task(_candle_processor(), name=f"candle-proc-{symbol}")
    task_trade = asyncio.create_task(_trade_processor(), name=f"trade-proc-{symbol}")
    _execution_state["ws_tasks"] = [task_candle, task_trade]

    # Log how many frontend WS clients are connected
    ws_count = len(_scalping_ws_connections)
    logger.info(f"BinanceWSClient started for {symbol} — {ws_count} frontend WS client(s) connected")

    # Log expected WS URL for debugging
    from app.config import settings as cfg
    base = cfg.binance_ws_base_url.rstrip('/')
    expected_url = f"{base.replace('/ws', '/stream')}?streams={symbol.lower()}@kline_1m/{symbol.lower()}@trade"
    logger.info(f"Expected Binance stream URL: {expected_url}")


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
    """Get historical intelligence snapshots.
    
    TODO: Caricare da Supabase tabella market_intel_snapshots quando disponibile.
    """
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
        session["started_at"] = _now()
        session["stopped_at"] = None

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
        # Stop BinanceWSClient and pipeline
        asyncio.create_task(
            _stop_ws_broadcast(),
            name="scalping-ws-stop",
        )
        
        session["status"] = "idle"
        session["session_id"] = None
        session["started_at"] = None
        session["stopped_at"] = _now()

    elif action == "pause":
        if session["status"] == "running":
            session["status"] = "paused"

    elif action == "resume":
        if session["status"] == "paused":
            session["status"] = "running"

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
    
    # Calculate max drawdown from running PnL
    running_pnl = 0
    peak = 0
    max_dd = 0
    for t in trades:
        running_pnl += t.get("pnl", 0)
        if running_pnl > peak:
            peak = running_pnl
        dd = peak - running_pnl
        if dd > max_dd:
            max_dd = dd
    
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
    
    return {
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": 0,  # Would need initial capital
        "win_rate": round(win_count / total * 100, 2) if total else 0,
        "total_trades": total,
        "winning_trades": win_count,
        "losing_trades": lose_count,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "profit_factor": profit_factor,
        "max_drawdown": round(max_dd, 2),
        "consecutive_losses": cons_losses,
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

    return [
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