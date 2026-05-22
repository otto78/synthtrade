"""StrategySelector - sceglie strategia in base al regime."""

from typing import Optional

from app.scalping.models.market import MarketRegime
from app.scalping.strategies.registry import StrategyRegistry
from app.scalping.strategies.base import AbstractScalpingStrategy


class StrategySelector:
    """Seleziona la strategia appropriata in base al regime di mercato.

    Mapping regime -> strategia ottimale.
    """

    _regime_strategy_map = {
        "trending_up": "ema_cross",      # Follow the trend
        "trending_down": "ema_cross",    # Follow the trend
        "ranging": "rsi_bollinger",      # Mean reversion
        "volatile": "vwap_reversion",     # VWAP as anchor
        "unknown": "ema_cross",          # Default
    }

    def select(self, regime: MarketRegime) -> Optional[AbstractScalpingStrategy]:
        """Select strategy for given market regime.

        Args:
            regime: MarketRegime detected by RegimeDetector.

        Returns:
            Strategy instance or None if not found.
        """
        strategy_name = self._regime_strategy_map.get(regime.regime, "ema_cross")
        return StrategyRegistry.get(strategy_name)

    def get_name_for_regime(self, regime: MarketRegime) -> str:
        """Get strategy name for regime without loading instance."""
        return self._regime_strategy_map.get(regime.regime, "ema_cross")