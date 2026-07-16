"""StrategySelector - sceglie strategia in base al regime (DB-driven).

TASK-904: Mapping letto da ScalpingConfigLoader (DB scalping_runtime_config)
invece di hardcoded. Default rimane hardcoded nel config_loader per retrocompatibilità.
"""

from typing import Optional

from app.scalping.models.market import MarketRegime
from app.scalping.strategies.registry import StrategyRegistry
from app.scalping.strategies.base import AbstractScalpingStrategy


class StrategySelector:
    """Seleziona la strategia appropriata in base al regime di mercato.

    Mapping letto da ScalpingConfigLoader con chiavi DB:
      REGIME_STRATEGY_trending_up = ema_cross
      REGIME_STRATEGY_ranging = rsi_bollinger
      REGIME_STRATEGY_volatile = stoch_rsi_bb_squeeze
      REGIME_STRATEGY_unknown = momentum_base
    """

    def __init__(self, regime_strategy_map: Optional[dict[str, str]] = None):
        self._regime_strategy_map = regime_strategy_map

    def _get_map(self) -> dict[str, str]:
        """Ritorna mapping da config_loader se disponibile, altrimenti da init."""
        if self._regime_strategy_map is not None:
            return self._regime_strategy_map
        # Fallback: carica da config_loader singleton
        try:
            from app.scalping.config_loader import get_scalping_config
            return get_scalping_config().regime_strategy_map
        except Exception:
            # Fallback hardcoded se config_loader non disponibile
            return {
                "trending_up": "ema_cross",
                "trending_down": "ema_cross",
                "ranging": "rsi_bollinger",
                "volatile": "stoch_rsi_bb_squeeze",
                "unknown": "momentum_base",
            }

    def select(self, regime: MarketRegime) -> Optional[AbstractScalpingStrategy]:
        """Select strategy for given market regime.

        Args:
            regime: MarketRegime detected by RegimeDetector.

        Returns:
            Strategy instance or None if not found.
        """
        strategy_name = self._get_map().get(regime.regime, "ema_cross")
        return StrategyRegistry.get(strategy_name)

    def get_name_for_regime(self, regime: MarketRegime) -> str:
        """Get strategy name for regime without loading instance."""
        return self._get_map().get(regime.regime, "ema_cross")
