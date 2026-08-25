"""StrategySelector - sceglie strategia in base al regime (DB-driven).

TASK-904: Mapping letto da ScalpingConfigLoader (DB scalping_runtime_config)
invece di hardcoded. Default rimane hardcoded nel config_loader per retrocompatibilità.
TASK-1250: Se BTC > EMA20 4h e regime è ranging, forza ema_cross (trend-following)
invece di rsi_bollinger (mean-reversion). Macro context passato da execution_loop.
"""

import logging
from typing import Optional

from app.scalping.models.market import MarketRegime
from app.scalping.strategies.registry import StrategyRegistry
from app.scalping.strategies.base import AbstractScalpingStrategy

logger = logging.getLogger(__name__)

# TASK-1250: strategie mean-reversion che vengono overridate da macro trend
_MEAN_REVERSION_STRATEGIES = frozenset(["rsi_bollinger", "stoch_rsi_bb_squeeze", "vwap_reversion"])


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
                "trending_down": "rsi_bollinger",
                "ranging": "rsi_bollinger",
                "volatile": "vwap_reversion",
                "unknown": "vwap_reversion",
            }

    def _apply_macro_override(
        self,
        regime: MarketRegime,
        strategy_name: str,
        macro_context: Optional[dict],
    ) -> str:
        """TASK-1250: Override macro trend — se BTC > EMA20 4h e strategia è mean-reversion,
        forza ema_cross (trend-following).

        Logica:
          - Solo se macro_context è disponibile e contiene btc_ema20_4h > 0
          - Solo se btc_price_at_entry > btc_ema20_4h (BTC sopra EMA20 4h)
          - Solo se la strategia selezionata dal regime è mean-reversion
            (rsi_bollinger, stoch_rsi_bb_squeeze, vwap_reversion)
          - NON si applica se il regime è già trending_up o trending_down
            (in quel caso il regime detector ha già scelto correttamente)
        """
        if not macro_context:
            return strategy_name

        btc_price = macro_context.get("btc_price_at_entry", 0.0) or 0.0
        ema20_4h = macro_context.get("btc_ema20_4h", 0.0) or 0.0

        if ema20_4h <= 0 or btc_price <= 0:
            return strategy_name

        # Non applicare se il regime è già correttamente trending
        if regime.regime in ("trending_up", "trending_down"):
            return strategy_name

        # Override solo se BTC sopra EMA20 4h e strategia è mean-reversion
        if btc_price > ema20_4h and strategy_name in _MEAN_REVERSION_STRATEGIES:
            logger.info(
                f"[Strategy] TASK-1250 MACRO OVERRIDE: "
                f"BTC {btc_price:.0f} > EMA20 4h {ema20_4h:.0f} → "
                f"override {strategy_name} → ema_cross (regime={regime.regime})"
            )
            return "ema_cross"

        return strategy_name

    def select(
        self,
        regime: MarketRegime,
        macro_context: Optional[dict] = None,
    ) -> Optional[AbstractScalpingStrategy]:
        """Select strategy for given market regime.

        Args:
            regime: MarketRegime detected by RegimeDetector.
            macro_context: Optional dict with BTC macro data (btc_price_at_entry,
                btc_ema20_4h). If BTC > EMA20 4h and regime maps to mean-reversion,
                overrides to ema_cross (TASK-1250).

        Returns:
            Strategy instance or None if not found.
        """
        strategy_name = self._get_map().get(regime.regime, "ema_cross")
        strategy_name = self._apply_macro_override(regime, strategy_name, macro_context)
        logger.info(f"[Strategy] selected={strategy_name} for regime={regime.regime}")
        return StrategyRegistry.get(strategy_name)

    def get_name_for_regime(
        self,
        regime: MarketRegime,
        macro_context: Optional[dict] = None,
    ) -> str:
        """Get strategy name for regime without loading instance."""
        strategy_name = self._get_map().get(regime.regime, "ema_cross")
        return self._apply_macro_override(regime, strategy_name, macro_context)
