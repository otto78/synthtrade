"""
strategy_runner.py
------------------
Core logic to execute a single tick for an ACTIVE strategy.

Responsibilities:
- Fetch recent OHLCV data.
- Compute technical signals based on strategy templates.
- Delegate signal processing to ExecutionEngine if a signal is triggered.
- Update strategy metadata (last_tick_at) in the database.

Key Dependencies: market_data, indicators, execution_engine, supabase_client
"""
import logging
from datetime import datetime, timezone

from app.core.market_data import fetch_ohlcv
from app.core.indicators import signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb
from app.db.supabase_client import get_supabase
from app.execution.execution_engine import ExecutionEngine
from app.execution.schemas import Signal
from app.execution.order_tracker import OrderTracker

logger = logging.getLogger(__name__)

# Template mapping -> Signal function (aligned with run_pipeline.py)
SIGNAL_MAP = {
    "trend_ema": lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]),
    "mean_reversion_rsi": lambda df, p: signal_rsi_reversion(
        df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]
    ),
    "breakout_bb": lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]),
}

# Minimum candles required for reliable indicator calculation
LOOKBACK_CANDLES = 200


def _extract_symbols(strategy: dict) -> list[str]:
    """
    Extracts the list of symbols to operate on.
    Supports both single pair (strategy["pair"]) and multi-asset (params.allocation).
    """
    params = strategy.get("params") or {}
    allocation = params.get("allocation")
    if allocation and isinstance(allocation, list):
        return [item["symbol"] for item in allocation if "symbol" in item]
    return [strategy.get("pair", "BTC/USDT")]


def _signal_to_direction(signal_value: int) -> str | None:
    """Converts numeric signal (-1, 0, 1) to string direction."""
    if signal_value == 1:
        return "BUY"
    if signal_value == -1:
        return "SELL"
    return None


class StrategyRunner:
    """
    Executes the signal loop for an ACTIVE strategy.
    Injected with the ExecutionEngine singleton during app lifespan.
    """

    def __init__(self, engine: ExecutionEngine):
        self.engine = engine
        self.db = get_supabase()

    async def run_tick(self, strategy: dict) -> None:
        """
        Executes a single tick for the given strategy:
        1. For each symbol, fetch OHLCV and compute signals.
        2. If a signal is generated, delegate to ExecutionEngine.process_signal().
        3. Update last_tick_at in the database.

        Exceptions are caught and logged to prevent the entire loop from failing.
        """
        strategy_id = strategy["id"]
        template = strategy.get("template", "")
        params = strategy.get("params") or {}
        timeframe = strategy.get("timeframe", "1h")

        if template not in SIGNAL_MAP:
            logger.warning(f"[{strategy_id}] Template '{template}' not supported, skipping.")
            return

        signal_fn = SIGNAL_MAP[template]
        symbols = _extract_symbols(strategy)

        for symbol in symbols:
            try:
                # 1. Fetch recent OHLCV
                df = fetch_ohlcv(symbol, timeframe, days=3)
                if df is None or len(df) < 50:
                    logger.warning(f"[{strategy_id}] Insufficient OHLCV for {symbol}, skipping.")
                    continue

                # 2. Compute signal
                raw_signal = signal_fn(df, params)
                # Signals return a pandas Series: take the latest value
                last_signal = int(raw_signal.iloc[-1]) if hasattr(raw_signal, "iloc") else int(raw_signal)
                direction = _signal_to_direction(last_signal)

                if direction is None:
                    logger.debug(f"[{strategy_id}] Neutral signal for {symbol}, proceeding with placeholder.")
                    direction = "HOLD"

                # 3. Build Signal and pass it to the engine
                current_price = float(df["close"].iloc[-1])
                signal = Signal(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    direction=direction,
                    strength=abs(last_signal),
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                )

                # --- DRAWDOWN CALCULATION (TASK-415) ---

                # Retrieve all open positions for this strategy to calculate global unrealized PnL
                strategy_positions = self.engine.order_tracker.get_open_positions(strategy_id=strategy_id)

                unrealized_pnl_usdt = 0.0
                for pos in strategy_positions:
                    # Use current_price if it matches the current symbol, otherwise fetch ticker from exchange
                    pos_price = current_price if pos.symbol == symbol else await self.engine.exchange.get_ticker_price(pos.symbol)
                    unrealized_pnl_usdt += self.engine.order_tracker.update_unrealized_pnl(
                        pos.entry_price, pos_price, pos.quantity, pos.direction
                    )

                realized_pnl_usdt = self.engine.order_tracker.get_realized_pnl(strategy_id)
                # Ensure numeric totals; if mocks return non‑numeric values, treat as zero
                if not isinstance(realized_pnl_usdt, (int, float)):
                    realized_pnl_usdt = 0.0
                if not isinstance(unrealized_pnl_usdt, (int, float)):
                    unrealized_pnl_usdt = 0.0
                total_pnl_usdt = realized_pnl_usdt + unrealized_pnl_usdt

                initial_capital = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
                current_equity = initial_capital + total_pnl_usdt

                # Peak-to-Trough logic:
                # The peak is either the initial capital, the stored peak, or the current equity
                stored_peak = strategy.get("peak_equity_usdt")
                peak_equity = max(initial_capital, float(stored_peak) if stored_peak else 0.0, current_equity)

                # Update peak_equity_usdt in the local dictionary so it can be saved at the end of the tick
                strategy["peak_equity_usdt"] = peak_equity

                # Calculate current drawdown percentage relative to the peak equity
                current_drawdown_pct = 0.0
                if current_equity < peak_equity:
                    current_drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100

                # --------------------------------------

                # Calcola il budget per questo simbolo in base all'allocazione (percentuale) se presente
                total_budget = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
                allocation = params.get("allocation") or []
                # Determina la percentuale di allocazione per il simbolo corrente
                pct = None
                if isinstance(allocation, list) and allocation:
                    for a in allocation:
                        if a.get("symbol") == symbol and isinstance(a.get("pct"), (int, float)):
                            pct = a["pct"]
                            break
                # Se non è stata trovata un'allocazione specifica, distribuisci equamente il budget tra i simboli
                if pct is None:
                    # Se ci sono più simboli, assegna una quota uguale; altrimenti 100%
                    pct = 100.0 / len(symbols) if len(symbols) > 0 else 100.0
                budget_usdt = total_budget * (pct / 100.0)
                await self.engine.process_signal(
                    signal=signal,
                    balance=budget_usdt,
                    open_positions=strategy_positions,
                    current_drawdown_pct=current_drawdown_pct,
                )
                logger.info(f"[{strategy_id}] Signal {direction} on {symbol} @ {current_price:.4f} processed.")

            except Exception as e:
                logger.error(f"[{strategy_id}] Tick error on {symbol}: {e}", exc_info=True)
                # Continue with remaining symbols (best-effort)

        # 4. Update last_tick_at metadata
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            update_data = {
                "last_tick_at": now_iso,
                "peak_equity_usdt": strategy.get("peak_equity_usdt")
            }
            self.db.table("strategies").update(update_data).eq("id", strategy_id).execute()
        except Exception as e:
            logger.warning(f"[{strategy_id}] Error updating last_tick_at: {e}")
