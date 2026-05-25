"""ExecutionLoop - main loop scalping v2.0.

Orchestrazione completa del processo di trading ad alta frequenza.
Può riutilizzare RiskManager (app/execution/risk_manager.py) e
BinanceExchangeAdapter (app/execution/exchange.py) dal core se forniti.
"""

import asyncio
import logging
from typing import Optional, Callable, Any

from app.scalping.data.candle_buffer import CandleBuffer
from app.scalping.engine.regime_detector import RegimeDetector
from app.scalping.engine.strategy_selector import StrategySelector
from app.scalping.engine.signal_aggregator import SignalAggregator
from app.scalping.engine.position_manager import PositionManager
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.models.market import Candle, MarketRegime
from app.scalping.engine.signal_aggregator import TechnicalSignal, ExecutionDecision

logger = logging.getLogger(__name__)


class ExecutionLoop:
    """Main execution loop per lo scalping.

    Gira ogni 500ms-2s processando candele e generando segnali.
    Può opzionalmente riutilizzare RiskManager e BinanceExchangeAdapter dal core.
    """

    def __init__(
        self,
        symbol: str,
        candle_buffer: Optional[CandleBuffer] = None,
        signal_engine: Optional[SignalScoreEngine] = None,
        signal_aggregator: Optional[SignalAggregator] = None,
        regime_detector: Optional[RegimeDetector] = None,
        strategy_selector: Optional[StrategySelector] = None,
        position_manager: Optional[PositionManager] = None,
        risk_manager: Optional[Any] = None,  # app.execution.risk_manager.RiskManager
        exchange: Optional[Any] = None,  # app.execution.exchange.BinanceExchangeAdapter
    ):
        self._symbol = symbol
        self._candle_buffer = candle_buffer or CandleBuffer()
        self._signal_engine = signal_engine or SignalScoreEngine(symbol=self._symbol)
        self._signal_aggregator = signal_aggregator or SignalAggregator()
        self._regime_detector = regime_detector or RegimeDetector()
        self._strategy_selector = strategy_selector or StrategySelector()
        self._position_manager = position_manager or PositionManager()
        self._risk_manager = risk_manager  # Opzionale
        self._exchange = exchange  # Opzionale
        self._strategy: Optional[AbstractScalpingStrategy] = None
        self._current_regime: Optional[MarketRegime] = None
        self._running = False
        self._indicators: dict = {}
        # Callback per eventi
        self._on_signal: Optional[Callable] = None
        self._on_trade: Optional[Callable] = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def regime(self) -> Optional[MarketRegime]:
        return self._current_regime

    @property
    def strategy(self) -> Optional[AbstractScalpingStrategy]:
        return self._strategy

    def set_signal_callback(self, callback: Optional[Callable]) -> None:
        """Set callback per segnali generati."""
        self._on_signal = callback

    def set_trade_callback(self, callback: Optional[Callable]) -> None:
        """Set callback per trade eseguiti."""
        self._on_trade = callback

    async def process_candle(self, candle: Candle) -> Optional[ExecutionDecision]:
        """Processa una candela e genera un eventuale ordine."""
        self._candle_buffer.add(candle)

        if not self._candle_buffer.is_ready():
            return None

        candles = self._candle_buffer.get()

        # 1. Calcola indicatori
        self._indicators = AbstractScalpingStrategy.calculate_indicators(candles)

        # 2. Detect regime (usa detect_trend/detect_volatility da app/core/indicators.py via RegimeDetector)
        self._current_regime = self._regime_detector.detect(candles, self._indicators)

        # 3. Select strategy
        self._strategy = self._strategy_selector.select(self._current_regime)

        if not self._strategy:
            return None

        # 4. Generate technical signal
        technical_signal = self._strategy.evaluate(candles, self._indicators)

        # 5. Get market intelligence score
        market_score = await self._signal_engine.compute()

        # 6. Aggregate signals
        decision = self._signal_aggregator.should_execute(technical_signal, market_score)

        # 7. Risk check via RiskManager core (opzionale, se fornito)
        if decision and decision.execute and self._risk_manager:
            try:
                risk_result = self._risk_manager.check_drawdown(0.0)
                if not risk_result.approved:
                    logger.warning(f"Risk check bloccato: {risk_result.reason}")
                    decision = ExecutionDecision(
                        execute=False,
                        reason=f"Risk block: {risk_result.reason}",
                        confidence=0.0,
                    )
                    return decision
            except Exception as exc:
                logger.warning(f"Risk check fallito (non bloccante): {exc}")

        # 8. Notify
        if self._on_signal and decision and decision.execute:
            await self._on_signal(decision, market_score, technical_signal)

        return decision

    async def on_trade(self, trade_data: dict) -> None:
        """Callback quando un trade viene eseguito."""
        logger.info(f"Trade executed: {trade_data}")
        if self._on_trade:
            await self._on_trade(trade_data)

    async def start(self) -> None:
        """Avvia il loop (placeholder per ora - verrà integrato con WS)."""
        self._running = True
        logger.info(f"ExecutionLoop started for {self._symbol}")

    async def stop(self) -> None:
        """Ferma il loop."""
        self._running = False
        logger.info(f"ExecutionLoop stopped for {self._symbol}")