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

# ANSI color codes for logs
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


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
        self.session_id: Optional[str] = None
        self.paper_mode: bool = True  # Default paper — impostato da router al session start
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

    def set_params(self, params: dict) -> None:
        """Update strategy parameters (used by supervisor)."""
        if self._strategy and hasattr(self._strategy, "update_params"):
            self._strategy.update_params(params)
            logger.info(f"Strategy params updated: {params}")
        else:
            logger.warning(f"Cannot update params: strategy has no update_params method. Params: {params}")

    def set_strategy(self, strategy_name: str) -> None:
        """Set strategy directly by name (used by supervisor)."""
        from app.scalping.strategies.registry import StrategyRegistry
        self._strategy = StrategyRegistry.get(strategy_name)

    def set_signal_callback(self, callback: Optional[Callable]) -> None:
        """Set callback per segnali generati."""
        self._on_signal = callback

    def set_trade_callback(self, callback: Optional[Callable]) -> None:
        """Set callback per trade eseguiti."""
        self._on_trade = callback

    async def process_candle(self, candle: Candle) -> Optional[ExecutionDecision]:
        """Processa una candela e genera un eventuale ordine."""
        buf_before = len(self._candle_buffer)
        self._candle_buffer.add(candle)

        if not self._candle_buffer.is_ready():
            if buf_before == 0:
                logger.info(f"{CYAN}PIPELINE: buffer warmup started for {self._symbol} (need >=50 candles){RESET}")
            elif buf_before % 10 == 0:
                logger.info(f"{YELLOW}PIPELINE: buffer {buf_before}/50 candles for {self._symbol}{RESET}")
            return None

        candles = self._candle_buffer.get()

        # 1. Calcola indicatori
        self._indicators = AbstractScalpingStrategy.calculate_indicators(candles)

        # 2. Detect regime (usa detect_trend/detect_volatility da app/core/indicators.py via RegimeDetector)
        self._current_regime = self._regime_detector.detect(candles, self._indicators)

        # 3. Select strategy
        self._strategy = self._strategy_selector.select(self._current_regime)

        if not self._strategy:
            logger.warning(f"{YELLOW}PIPELINE: no strategy selected for regime={self._current_regime.regime if self._current_regime else 'N/A'}{RESET}")
            return None

        # 4. Generate technical signal
        technical_signal = self._strategy.evaluate(candles, self._indicators)

        # 5. Get market intelligence score
        market_score = await self._signal_engine.compute()

        # 6. Log pipeline state
        regime_name = self._current_regime.regime if self._current_regime else "N/A"
        logger.info(
            f"{CYAN}PIPELINE: {self._symbol} regime={regime_name} "
            f"strategy={self._strategy.name} "
            f"tech={technical_signal.type}@{technical_signal.confidence:.2f} "
            f"intel={market_score.total:.1f} ({market_score.bias}) "
            f"tradeable={market_score.tradeable}{RESET}"
        )

        # 7. Aggregate signals
        decision = self._signal_aggregator.should_execute(
            technical_signal, market_score, symbol=self._symbol, paper_mode=self.paper_mode
        )

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