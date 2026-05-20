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
import pandas as pd

from app.core.market_data import fetch_ohlcv
from app.db.supabase_client import get_supabase
from app.execution.execution_engine import ExecutionEngine
from app.execution.schemas import Signal
from app.execution.registry import registry

logger = logging.getLogger(__name__)

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


from typing import Literal

def _signal_to_direction(signal_value: int) -> Literal["BUY", "SELL"] | None:
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
        2. Accumulate signals and delegate to ExecutionEngine.process_signals().
        3. Update last_tick_at in the database.

        Exceptions are caught and logged to prevent the entire loop from failing.
        """
        strategy_id = strategy["id"]
        template = strategy.get("template", "")
        params = strategy.get("params") or {}
        timeframe = strategy.get("timeframe", "1h")

        signal_fn = registry.get(template)
        if signal_fn is None:
            logger.warning(f"[{strategy_id}] Template '{template}' not supported, skipping.")
            return

        symbols = _extract_symbols(strategy)
        collected_signals: list[Signal] = []
        
        # Calculate shared metrics (drawdown) once per tick if possible
        # Retrieve all open positions for this strategy to calculate global unrealized PnL
        strategy_positions = self.engine.order_tracker.get_open_positions(strategy_id=strategy_id)
        realized_pnl_usdt = self.engine.order_tracker.get_realized_pnl(strategy_id)
        if not isinstance(realized_pnl_usdt, (int, float)):
            realized_pnl_usdt = 0.0

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
                if isinstance(raw_signal, pd.Series):
                    last_signal = int(raw_signal.iloc[-1])
                else:
                    last_signal = int(raw_signal)
                direction = _signal_to_direction(last_signal)

                current_price = float(df["close"].iloc[-1])

                if direction is not None:
                    signal = Signal(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        direction=direction,
                        strength=abs(last_signal),
                        price=current_price,
                        timestamp=datetime.now(timezone.utc),
                    )
                    collected_signals.append(signal)

            except Exception as e:
                logger.error(f"[{strategy_id}] Signal computation error on {symbol}: {e}")

        # --- DRAWDOWN CALCULATION (TASK-415) ---
        try:
            unrealized_pnl_usdt = 0.0
            for pos in strategy_positions:
                # Fetch current price for each open position
                # Optimization: if symbol is in our scan, we already have it, otherwise fetch
                pos_price = await self.engine.exchange.get_ticker_price(pos.symbol)
                unrealized_pnl_usdt += self.engine.order_tracker.update_unrealized_pnl(
                    pos.entry_price, pos_price, pos.quantity, pos.direction
                )

            if not isinstance(unrealized_pnl_usdt, (int, float)):
                unrealized_pnl_usdt = 0.0
            total_pnl_usdt = realized_pnl_usdt + unrealized_pnl_usdt

            initial_capital = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
            current_equity = initial_capital + total_pnl_usdt

            stored_peak = strategy.get("peak_equity_usdt")
            peak_equity = max(initial_capital, float(stored_peak) if stored_peak else 0.0, current_equity)
            strategy["peak_equity_usdt"] = peak_equity

            current_drawdown_pct = 0.0
            if current_equity < peak_equity:
                current_drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100

            # --------------------------------------

            # 3. Delegate signal processing to ExecutionEngine
            if collected_signals:
                # Note: balance used here is total budget for simplicity in this refactor, 
                # though individual symbols might have allocations. 
                # DefaultSignalResolver will filter/prioritize.
                total_budget = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
                await self.engine.process_signals(
                    signals=collected_signals,
                    balance=total_budget,
                    current_drawdown_pct=current_drawdown_pct
                )
                logger.info(f"[{strategy_id}] Processed {len(collected_signals)} signals.")

        except Exception as e:
            logger.error(f"[{strategy_id}] Tick finalization error: {e}", exc_info=True)

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
