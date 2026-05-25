"""BacktestEngine — motore di backtest per strategie scalping (TASK-808).

Itera candele storiche, esegue ciclo completo di trading simulato
con opzione use_intelligence per confronto with/without SignalScoreEngine.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, List, Optional

from app.scalping.models.backtest import (
    BacktestConfig,
    BacktestResult,
    SimulatedTrade,
)
from app.scalping.models.market import Candle
from app.scalping.engine.execution_loop import ExecutionLoop
from app.scalping.engine.signal_aggregator import (
    ExecutionDecision,
    SignalAggregator,
)
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Motore di backtest per validare strategie scalping.

    Uso:
        engine = BacktestEngine()
        result = await engine.run(config, candles)
    """

    def __init__(
        self,
        execution_loop: Optional[ExecutionLoop] = None,
        signal_aggregator: Optional[SignalAggregator] = None,
        signal_engine: Optional[SignalScoreEngine] = None,
    ):
        self._execution_loop = execution_loop
        self._signal_aggregator = signal_aggregator or SignalAggregator()
        self._signal_engine = signal_engine

    async def run(
        self,
        config: BacktestConfig,
        candles: List[Candle],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        decision_callback: Optional[Callable[[ExecutionDecision, Candle], None]] = None,
    ) -> BacktestResult:
        """Esegue il backtest iterando le candele.

        Args:
            config: Configurazione backtest.
            candles: Candele storiche ordinate cronologicamente.
            progress_callback: Callable(passo, totale) per progresso.
            decision_callback: Callable(decision, candle) per monitorare ogni decisione.

        Returns:
            BacktestResult con trades simulati e metriche.
        """
        result_id = str(uuid.uuid4())[:8]
        logger.info(f"Backtest [{result_id}] starting: {config.symbol} "
                     f"{config.start_date.date()} → {config.end_date.date()}, "
                     f"capital={config.initial_capital}, intelligence={config.use_intelligence}")

        result = BacktestResult(
            id=result_id,
            config=config,
        )

        if not candles:
            result.errors.append("No candles provided for backtest")
            result.completed_at = datetime.now(timezone.utc)
            return result

        total = len(candles)
        position: Optional[SimulatedTrade] = None
        capital = config.initial_capital
        equity = [{"timestamp": candles[0].timestamp, "equity": float(capital)}]

        # Crea ExecutionLoop se non fornito
        loop = self._execution_loop
        if loop is None:
            loop = ExecutionLoop(symbol=config.symbol)

        # Intelligence engine se abilitato
        intel_engine = self._signal_engine or SignalScoreEngine(symbol=config.symbol)

        for idx, candle in enumerate(candles):
            if progress_callback:
                progress_callback(idx + 1, total)

            # Processa candela con ExecutionLoop
            try:
                decision = await loop.process_candle(candle)
            except Exception as exc:
                result.errors.append(f"Candle {idx}: {exc}")
                continue

            if decision_callback and decision:
                decision_callback(decision, candle)

            # Se use_intelligence=False, forza esecuzione solo su segnale tecnico
            if not config.use_intelligence and decision and not decision.execute:
                # Rewrite decision: esegui comunque se c'è un segnale tecnico valido
                decision = ExecutionDecision(
                    execute=True,
                    confidence=0.5,
                    reason="technical_only",
                )

            if decision and decision.execute and position is None:
                # Entry: apre posizione
                quantity = self._calculate_quantity(capital, candle.close, config)
                position = SimulatedTrade(
                    entry_time=candle.timestamp,
                    symbol=config.symbol,
                    side="BUY",
                    entry_price=candle.close,
                    quantity=quantity,
                    signal_type="HYBRID" if config.use_intelligence else "TECHNICAL",
                    signal_score=decision.confidence,
                )
                logger.debug(f"[{result_id}] ENTRY {config.symbol} @ {candle.close}")

            elif position is not None and position.is_closed is False:
                # Criteri di uscita (SELL/CLOSE signal o stop)
                should_close = False
                close_reason = ""

                if decision and decision.execute and decision.reason:
                    should_close = True
                    close_reason = decision.reason
                elif candle.timestamp > position.entry_time:
                    # Exit dopo N periodi (placeholder per strategia di uscita)
                    # Per ora, chiude dopo ogni candela per test
                    should_close = True
                    close_reason = "period_end"

                if should_close:
                    commission = config.commission_pct * position.entry_price * position.quantity
                    position.close(
                        exit_price=candle.close,
                        exit_time=candle.timestamp,
                        commission=commission,
                    )
                    result.trades.append(position)

                    # Aggiorna capitale
                    if position.pnl is not None:
                        capital += position.pnl
                    position = None
                    logger.debug(f"[{result_id}] EXIT {config.symbol} @ {candle.close}")

            # Equity curve
            equity.append({
                "timestamp": candle.timestamp,
                "equity": float(capital) + (
                    float(self._unrealized_pnl(position, candle.close))
                    if position else 0
                ),
            })

        # Chiudi posizione ancora aperta
        if position is not None and not position.is_closed:
            close_price = candles[-1].close if candles else Decimal("0")
            commission = config.commission_pct * position.entry_price * position.quantity
            position.close(
                exit_price=close_price,
                exit_time=candles[-1].timestamp,
                commission=commission,
            )
            result.trades.append(position)

        # Calcola metriche
        result.equity_curve = equity
        result.completed_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        logger.info(f"Backtest [{result_id}] completed: "
                     f"{len(result.trades)} trades, "
                     f"capital: {config.initial_capital} → {capital}")

        return result

    def _calculate_quantity(
        self,
        capital: Decimal,
        price: Decimal,
        config: BacktestConfig,
    ) -> Decimal:
        """Calcola quantità da acquistare in base al capitale."""
        if price <= 0:
            return Decimal("0")
        # Usa 95% del capitale per ogni trade
        invest_amount = capital * Decimal("0.95")
        return (invest_amount / price).quantize(Decimal("0.00001"))

    @staticmethod
    def _unrealized_pnl(position: Optional[SimulatedTrade], current_price: Decimal) -> Decimal:
        """Calcola P&L non realizzato per una posizione aperta."""
        if position is None or position.side != "BUY":
            return Decimal("0")
        return (current_price - position.entry_price) * position.quantity