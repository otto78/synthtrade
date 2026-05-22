"""CandleBuffer — buffer circolare per candele 1m.

Usato dall'ExecutionLoop per mantenere le ultime N candele.
"""

from collections import deque
from dataclasses import dataclass
from typing import List, Optional

from app.scalping.models.market import Candle


@dataclass
class CandleBufferConfig:
    """Configurazione del buffer."""
    size: int = 200  # Numero massimo di candele


class CandleBuffer:
    """Buffer circolare per candele 1m.

    L'ExecutionLoop aggiunge candele man mano che arrivano dallo WS.
    """

    def __init__(self, size: int = 200):
        self._size = size
        self._buffer: deque = deque(maxlen=size)

    def add(self, candle: Candle) -> None:
        """Aggiunge una candela al buffer."""
        self._buffer.append(candle)

    def get(self) -> List[Candle]:
        """Restituisce tutte le candele nel buffer."""
        return list(self._buffer)

    def is_ready(self, min_size: int = 50) -> bool:
        """Verifica se il buffer ha abbastanza candele per calcolare indicatori."""
        return len(self._buffer) >= min_size

    def clear(self) -> None:
        """Svuota il buffer."""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)

    def __getitem__(self, index: int) -> Candle:
        return self._buffer[index]

    @property
    def latest(self) -> Optional[Candle]:
        """Ultima candela aggiunta."""
        if not self._buffer:
            return None
        return self._buffer[-1]

    @property
    def previous(self) -> Optional[Candle]:
        """Penultima candela."""
        if len(self._buffer) < 2:
            return None
        return self._buffer[-2]