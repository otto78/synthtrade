from typing import Protocol, runtime_checkable
from app.execution.schemas import Signal, PositionSnapshot


@runtime_checkable
class SignalResolverProtocol(Protocol):
    def resolve(self, signals: list[Signal],
                open_positions: list[PositionSnapshot]) -> list[Signal]: ...


class DefaultSignalResolver:
    def __init__(self, strength_threshold: float = 0.6):
        self.strength_threshold = strength_threshold

    def resolve(self, signals: list[Signal],
                open_positions: list[PositionSnapshot]) -> list[Signal]:
        open_symbols = {p.symbol for p in open_positions}

        # Filtra per threshold e simboli già in posizione
        candidates = [
            s for s in signals
            if s.strength >= self.strength_threshold and s.symbol not in open_symbols
        ]

        # Per ogni symbol tieni solo il segnale con strength maggiore
        best: dict[str, Signal] = {}
        for s in candidates:
            if s.symbol not in best or s.strength > best[s.symbol].strength:
                best[s.symbol] = s

        return list(best.values())
