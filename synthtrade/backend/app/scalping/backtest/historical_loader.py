"""HistoricalLoader — caricamento dati storici per backtest (TASK-808).

Supporta:
- Binance REST API pubblica (nessuna API key necessaria per OHLCV storico)
- Caricamento da file CSV per test deterministici
"""

import csv
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from urllib.request import urlopen, Request

from app.scalping.models.market import Candle

logger = logging.getLogger(__name__)

# Mapping timeframe → Binance interval
BINANCE_INTERVALS = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d",
}

BINANCE_BASE_URL = "https://api.binance.com/api/v3/klines"


class HistoricalLoader:
    """Caricatore dati storici per backtest.

    Uso:
        loader = HistoricalLoader()
        candles = await loader.load_ohlcv("BTCUSDT", "1h", start, end)
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self._cache_dir = Path(cache_dir) if cache_dir else None

    async def load_ohlcv(
        self,
        symbol: str,
        interval: str = "1h",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Candle]:
        """Carica candele OHLCV da Binance REST API.

        Args:
            symbol: Simbolo, es: BTCUSDT.
            interval: Timeframe: 1m, 5m, 15m, 1h, 4h, 1d.
            start: Data inizio (opzionale).
            end: Data fine (opzionale).
            limit: Max candele per chiamata (max 1000).

        Returns:
            List[Candle] ordinate cronologicamente.
        """
        if interval not in BINANCE_INTERVALS:
            raise ValueError(f"Intervallo {interval} non supportato. Usa: {list(BINANCE_INTERVALS.keys())}")

        params = f"symbol={symbol}&interval={BINANCE_INTERVALS[interval]}&limit={limit}"

        if start:
            params += f"&startTime={int(start.timestamp() * 1000)}"
        if end:
            params += f"&endTime={int(end.timestamp() * 1000)}"

        url = f"{BINANCE_BASE_URL}?{params}"
        logger.debug(f"Fetching OHLCV: {url}")

        try:
            req = Request(url, headers={"User-Agent": "SynthTrade/1.0"})
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Errore caricamento OHLCV da Binance: {e}")
            return []

        candles = []
        for entry in data:
            try:
                candle = Candle(
                    symbol=symbol,
                    open=Decimal(str(entry[1])),
                    high=Decimal(str(entry[2])),
                    low=Decimal(str(entry[3])),
                    close=Decimal(str(entry[4])),
                    volume=Decimal(str(entry[5])),
                    timestamp=datetime.fromtimestamp(entry[0] / 1000, tz=timezone.utc),
                    closed=True,
                )
                candles.append(candle)
            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Errore parsing entry Binance: {entry[:6]}, err: {e}")
                continue

        # Filtra per date esatte se specificate
        if start:
            candles = [c for c in candles if c.timestamp >= start]
        if end:
            candles = [c for c in candles if c.timestamp <= end]

        return candles

    @staticmethod
    def load_from_csv(filepath: str, symbol: str) -> List[Candle]:
        """Carica candele da file CSV.

        Formato CSV atteso:
            timestamp,open,high,low,close,volume
            2026-01-01T00:00:00Z,50000.0,51000.0,49000.0,50500.0,100.5
        """
        candles = []
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"File CSV non trovato: {filepath}")

        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                    candle = Candle(
                        symbol=symbol,
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        volume=Decimal(str(row["volume"])),
                        timestamp=ts,
                        closed=True,
                    )
                    candles.append(candle)
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Errore parsing riga CSV: {row}, err: {e}")
                    continue

        return candles

    @staticmethod
    def generate_mock_candles(
        symbol: str,
        count: int = 100,
        start_price: Decimal = Decimal("50000"),
        volatility: Decimal = Decimal("0.01"),
    ) -> List[Candle]:
        """Genera candele mock per test.

        Crea una sequenza di candele con trend casuale simulato.
        """
        from random import seed, uniform

        candles = []
        price = float(start_price)
        current_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        vol = float(volatility)

        for i in range(count):
            change = uniform(-vol, vol) * price
            close_price = price + change
            high_price = max(price, close_price) * (1 + uniform(0, vol * 0.5))
            low_price = min(price, close_price) * (1 - uniform(0, vol * 0.5))
            volume = uniform(10, 1000)

            candle = Candle(
                symbol=symbol,
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(high_price, 2))),
                low=Decimal(str(round(low_price, 2))),
                close=Decimal(str(round(close_price, 2))),
                volume=Decimal(str(round(volume, 2))),
                timestamp=current_time,
                closed=True,
            )
            candles.append(candle)
            price = close_price
            current_time += _interval_timedelta("1h")

        return candles


def _interval_timedelta(interval: str):
    """Restituisce timedelta per un intervallo."""
    from datetime import timedelta
    mapping = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
    }
    return mapping.get(interval, timedelta(hours=1))
