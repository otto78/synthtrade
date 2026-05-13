"""
TASK-406: StrategyRunner
Esegue un tick per una singola strategia ACTIVE:
- Scarica OHLCV recenti
- Calcola il segnale tecnico
- Se positivo, chiama ExecutionEngine.process_signal()
- Aggiorna last_tick_at e logga su DB
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

# Mappa template → funzione segnale (stessa di run_pipeline.py)
SIGNAL_MAP = {
    "trend_ema": lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]),
    "mean_reversion_rsi": lambda df, p: signal_rsi_reversion(
        df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]
    ),
    "breakout_bb": lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]),
}

# Numero di candle necessari per il calcolo degli indicatori
LOOKBACK_CANDLES = 200


def _extract_symbols(strategy: dict) -> list[str]:
    """
    Estrae la lista di simboli su cui operare.
    Supporta sia il formato single (strategy["pair"]) che multi-asset (params.allocation).
    """
    params = strategy.get("params") or {}
    allocation = params.get("allocation")
    if allocation and isinstance(allocation, list):
        return [item["symbol"] for item in allocation if "symbol" in item]
    return [strategy.get("pair", "BTC/USDT")]


def _signal_to_direction(signal_value: int) -> str | None:
    """Converte il segnale numerico (-1, 0, 1) in direzione stringa."""
    if signal_value == 1:
        return "BUY"
    if signal_value == -1:
        return "SELL"
    return None


class StrategyRunner:
    """
    TASK-406: Esegue il loop di segnali per una strategia ACTIVE.
    Una sola istanza per l'intera app, riceve l'engine singleton dal lifespan.
    """

    def __init__(self, engine: ExecutionEngine):
        self.engine = engine
        self.db = get_supabase()

    async def run_tick(self, strategy: dict) -> None:
        """
        Esegue un singolo tick per la strategia:
        1. Per ogni simbolo della strategia, scarica OHLCV e calcola segnale
        2. Se segnale positivo, delega a ExecutionEngine.process_signal()
        3. Aggiorna last_tick_at su DB

        Non propaga eccezioni: errori vengono loggati e il tick viene saltato.
        """
        strategy_id = strategy["id"]
        template = strategy.get("template", "")
        params = strategy.get("params") or {}
        timeframe = strategy.get("timeframe", "1h")

        if template not in SIGNAL_MAP:
            logger.warning(f"[{strategy_id}] Template '{template}' non supportato, skip")
            return

        signal_fn = SIGNAL_MAP[template]
        symbols = _extract_symbols(strategy)

        for symbol in symbols:
            try:
                # 1. Scarica OHLCV recenti
                df = fetch_ohlcv(symbol, timeframe, days=3)
                if df is None or len(df) < 50:
                    logger.warning(f"[{strategy_id}] OHLCV insufficienti per {symbol}, skip")
                    continue

                # 2. Calcola segnale
                raw_signal = signal_fn(df, params)
                # I segnali restituiscono una Series pandas: prendiamo l'ultimo valore
                last_signal = int(raw_signal.iloc[-1]) if hasattr(raw_signal, "iloc") else int(raw_signal)
                direction = _signal_to_direction(last_signal)

                if direction is None:
                    logger.debug(f"[{strategy_id}] Segnale neutro per {symbol}, nessun ordine")
                    continue

                # 3. Costruisce il Signal e lo passa all'engine
                current_price = float(df["close"].iloc[-1])
                signal = Signal(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    direction=direction,
                    strength=abs(last_signal),
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                )

                # Recupera posizioni aperte e drawdown per il risk check
                open_positions = self.engine.order_tracker.get_open_positions(symbol)
                current_drawdown = 0.0  # TODO: calcolo drawdown da TASK-415

                budget_usdt = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
                await self.engine.process_signal(
                    signal=signal,
                    balance=budget_usdt,
                    open_positions=open_positions,
                    current_drawdown_pct=current_drawdown,
                )
                logger.info(f"[{strategy_id}] Segnale {direction} su {symbol} @ {current_price:.4f} processato")

            except Exception as e:
                logger.error(f"[{strategy_id}] Errore tick su {symbol}: {e}", exc_info=True)
                # Continua con i prossimi simboli (best-effort)

        # 4. Aggiorna last_tick_at
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            self.db.table("strategies").update({"last_tick_at": now_iso}).eq("id", strategy_id).execute()
        except Exception as e:
            logger.warning(f"[{strategy_id}] Errore aggiornamento last_tick_at: {e}")
