"""StrategySelector - sceglie strategia in base al regime."""

from typing import Optional

from app.scalping.models.market import MarketRegime
from app.scalping.strategies.registry import StrategyRegistry
from app.scalping.strategies.base import AbstractScalpingStrategy


class StrategySelector:
    """Seleziona la strategia appropriata in base al regime di mercato.

    Mapping regime -> strategia ottimale:
      - trending_up/down:  ema_cross (trend following)
      - ranging:           rsi_bollinger (mean reversion)
      - volatile:          stoch_rsi_bb_squeeze (cattura breakout)
      - unknown:           momentum_base (default sicuro)
    """

    _regime_strategy_map = {
<<<<<<< Updated upstream
        "trending_up": "ema_cross",              # Follow the trend
        "trending_down": "ema_cross",            # Follow the trend
        "ranging": "rsi_bollinger",              # Mean reversion per ranging
        "volatile": "stoch_rsi_bb_squeeze",      # Cattura breakout da volatilità
        "unknown": "momentum_base",              # Default sicuro
=======
        "trending_up": "ema_cross",          # Follow the trend
        "trending_down": "ema_cross",        # Follow the trend
        "ranging": "rsi_bollinger",          # Mean reversion per ranging
        "volatile": "stoch_rsi_bb_squeeze",  # Cattura breakout da volatilità
        "unknown": "momentum_base",          # Default sicuro
>>>>>>> Stashed changes
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