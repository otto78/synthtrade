"""Pipeline bootstrap: WS client, candle buffer warmup, processor tasks.

Extracted from router.py (TASK-1166.D). Contains _start_ws_broadcast and
_stop_ws_broadcast which manage the WS client lifecycle and processor tasks.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.config import settings
from app.scalping._state import _execution_state, _scalping_ws_connections
from app.scalping.broadcast import broadcast_scalping_event
from app.scalping.pricing import _get_fee_rate
from app.scalping.reconciliation import _reconcile_position_with_exchange
from app.scalping.db_ops import _update_closed_position_in_db

logger = logging.getLogger(__name__)


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
        f"[Pipeline] ENTERED for {symbol} | "
        f"session_status={session['status']} mode={session['mode']} "
        f"restore_mode={restore_mode}"
    )

    is_testnet = session.get("mode") != "live"
    guard = _execution_state.get("session_load_guard")

    # Create pipeline components FIRST (before WS client)
    from app.scalping.data.candle_buffer import CandleBuffer
    candle_buffer = CandleBuffer()
    signal_engine = _execution_state.get("signal_engine")
    if not signal_engine:
        from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
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
    logger.info(f"[Pipeline] _session_mode={_session_mode}")
    from app.scalping.engine.execution_loop import ExecutionLoop
    from app.scalping.engine.signal_aggregator import SignalAggregator
    from app.scalping.engine.regime_detector import RegimeDetector
    from app.scalping.engine.strategy_selector import StrategySelector
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
    # Must be False in live/demo mode so the full intelligence + technical filter applies.
    execution_loop.paper_mode = (_session_mode != "live" and not settings.exchange_demo)
    _execution_state["loop"] = execution_loop
    logger.info(f"[Pipeline] ExecutionLoop created, paper_mode={execution_loop.paper_mode}")

    # Warm up the candle buffer with historical candles BEFORE starting WS client.
    logger.info(f"[Pipeline] starting warmup...")
    try:
        from app.scalping.backtest.historical_loader import HistoricalLoader
        loader = HistoricalLoader()
        logger.info(f"[Pipeline] Pre-loading past 100 1m candles for {symbol.upper()} to warm up buffer...")
        past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=100)
        if past_candles:
            loaded_count = 0
            for c in past_candles:
                if hasattr(c, "timestamp") and hasattr(c, "open"):
                    candle_buffer.add(c)
                    loaded_count += 1
            logger.info(
                f"[Pipeline] Loaded {loaded_count} historical candles for {symbol} "
                f"(available via HTTP /candles/{symbol}). "
                f"Buffer size: {len(candle_buffer)}, ready: {candle_buffer.is_ready(50)}"
            )

            if len(execution_loop._candle_buffer) < 50:
                logger.info(
                    f"[Pipeline] Buffer sync: aligning execution_loop buffer with candle_buffer "
                    f"(candle_buffer len={len(candle_buffer)}, "
                    f"execution_loop buffer len={len(execution_loop._candle_buffer)}). "
                    f"Setting direct reference..."
                )
                execution_loop._candle_buffer = candle_buffer
                logger.info(
                    f"[Pipeline] Buffer sync complete. "
                    f"Buffer now: {len(execution_loop._candle_buffer)}, "
                    f"ready: {execution_loop._candle_buffer.is_ready(50)}"
                )

            if guard:
                guard.complete_phase("buffer_phase")

            if past_candles and loaded_count >= 50:
                from app.scalping.models.market import Candle
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
                            f"[Pipeline] FORCED FIRST: regime={execution_loop._current_regime.regime if execution_loop._current_regime else 'N/A'} "
                            f"strategy={execution_loop._strategy.name if execution_loop._strategy else 'N/A'} "
                            f"decision=execute={_d.execute} confidence={_d.confidence:.2f} reason='{_d.reason}' type={_d.signal_type}"
                        )
                except Exception as forced_err:
                    logger.warning(f"[Pipeline] Forced candle failed (non-fatal): {forced_err}")

        else:
            logger.warning(f"[Pipeline] No historical candles returned for {symbol}, buffer will warm up live.")
    except Exception as warmup_err:
        logger.error(f"[Pipeline] Warmup failed with historical data: {warmup_err}", exc_info=True)

    # TASK-1107: provider-neutral WS client via factory (OKX or Binance)
    from app.execution.exchange_factory import build_ws_client
    client = build_ws_client(symbols=[symbol])
    _execution_state["ws_client"] = client
    try:
        await asyncio.wait_for(client.start(), timeout=10.0)
        logger.info(f"[Pipeline] WS connected for {symbol}")
    except asyncio.TimeoutError:
        logger.warning(
            f"[Pipeline] WS timeout for {symbol} after 10s. "
            f"Pipeline will run with mock data and reconnect on next watchdog cycle."
        )
    except Exception as ws_e:
        logger.warning(f"[Pipeline] WS failed for {symbol}: {ws_e}. Running with mock data only.")

    if guard:
        guard.complete_phase("pipeline_phase")

    if restore_mode:
        try:
            pm = _execution_state["position_manager"]
            pos = pm.get_open()
            if pos:
                exchange = _execution_state.get("exchange")
                if exchange:
                    bracket_id = getattr(pos, 'oco_order_list_id', None)
                    reconcile = await _reconcile_position_with_exchange(
                        symbol=pos.symbol,
                        pos_side=pos.side,
                        entry_price=float(pos.entry_price),
                        quantity=float(pos.quantity),
                        exchange=exchange,
                        bracket_id=bracket_id,
                    )
                    if reconcile:
                        fp = reconcile["fill_price"]
                        entry_f = float(pos.entry_price)
                        qty_f = float(pos.quantity)
                        gross_pnl = (fp - entry_f) * qty_f if pos.side == "BUY" else (entry_f - fp) * qty_f
                        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
                        entry_fee_r = _get_fee_rate(fee_tier, "taker", 0.001)
                        exit_fee_r = _get_fee_rate(fee_tier, "taker", 0.001)
                        total_fees = (entry_f * qty_f * entry_fee_r) + (fp * qty_f * exit_fee_r)
                        pnl = gross_pnl - total_fees
                        pnl_pct = (pnl / (entry_f * qty_f)) * 100 if entry_f > 0 else 0

                        logger.info(
                            "[Pipeline] RECONCILE: Position was closed externally - "
                            "fill=%.4f reason=%s pnl=%.2f",
                            fp, reconcile["reason"], pnl
                        )
                        pm.close_position(Decimal(str(fp)))
                        await _update_closed_position_in_db(
                            pos, fp, pnl, pnl_pct, reconcile["reason"]
                        )
                        # FIX: append to trade_history so session counters are accurate
                        _execution_state["trade_history"].append({
                            "symbol": pos.symbol,
                            "side": pos.side,
                            "entry_price": entry_f,
                            "exit_price": fp,
                            "quantity": qty_f,
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "signal_reason": reconcile["reason"],
                        })
                        await broadcast_scalping_event("position_reconciled_externally", {
                            "symbol": pos.symbol,
                            "side": pos.side,
                            "entry_price": entry_f,
                            "exit_price": fp,
                            "quantity": qty_f,
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(pnl_pct, 2),
                            "reason": reconcile["reason"],
                            "source": reconcile["source"],
                        })
        except Exception as restore_e:
            logger.warning(f"[Pipeline] RECONCILE: Reconcile after WS connect failed: {restore_e}")

    # Pull events from WS client queues and broadcast to scalping WS clients
    from app.scalping.market_processors import _candle_processor, _trade_processor, _intelligence_processor

    def _task_done_cb(name, task):
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error(f"[Pipeline] {name} CRASHED with {type(exc).__name__}: {exc}", exc_info=exc)

    task_candle = asyncio.create_task(_candle_processor(symbol, restore_mode), name=f"candle-proc-{symbol}")
    task_candle.add_done_callback(lambda t: _task_done_cb("candle_processor", t))
    task_trade = asyncio.create_task(_trade_processor(symbol, restore_mode), name=f"trade-proc-{symbol}")
    task_trade.add_done_callback(lambda t: _task_done_cb("trade_processor", t))
    task_intel = asyncio.create_task(_intelligence_processor(symbol, restore_mode), name=f"intel-proc-{symbol}")
    task_intel.add_done_callback(lambda t: _task_done_cb("intel_processor", t))

    _execution_state["ws_tasks"] = [task_candle, task_trade, task_intel]

    ws_count = len(_scalping_ws_connections)
    logger.info(f"[Pipeline] Broadcast started for {symbol} — {ws_count} frontend WS client(s) connected")

    # Post-start actions for restore_mode
    if restore_mode:
        from app.scalping.market_processors import restore_mode_post_start
        await restore_mode_post_start(symbol)


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
