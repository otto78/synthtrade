"""Strategy Registry - gestione strategie scalping."""

from typing import Dict, Optional

from app.scalping.strategies.base import AbstractScalpingStrategy
from app.scalping.strategies.ema_cross import EMACrossStrategy
from app.scalping.strategies.rsi_bollinger import RSIBollingerStrategy
from app.scalping.strategies.vwap_reversion import VWAPReversionStrategy


class StrategyRegistry:
    """Registro delle strategie disponibili.

    Mappa nome strategia -> istanza.
    """

    _strategies: Dict[str, AbstractScalpingStrategy] = {}

    @classmethod
    def initialize(cls) -> None:
        """Inizializza tutte le strategie."""
        cls._strategies = {
            "ema_cross": EMACrossStrategy(),
            "rsi_bollinger": RSIBollingerStrategy(),
            "vwap_reversion": VWAPReversionStrategy(),
        }

    @classmethod
    def get(cls, name: str) -> Optional[AbstractScalpingStrategy]:
        """Ottieni una strategia per nome."""
        if not cls._strategies:
            cls.initialize()
        return cls._strategies.get(name)

    @classmethod
    def all(cls) -> Dict[str, AbstractScalpingStrategy]:
        """Restituisce tutte le strategie."""
        if not cls._strategies:
            cls.initialize()
        return cls._strategies.copy()

    @classmethod
    def names(cls) -> list:
        """Restituisce i nomi delle strategie disponibili."""
        if not cls._strategies:
            cls.initialize()
        return list(cls._strategies.keys())


# Inizializzazione automatica
StrategyRegistry.initialize()