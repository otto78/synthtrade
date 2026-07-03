"""HistoricalLoader — caricamento dati storici per backtest (TASK-808 / TASK-1110).

Supporta:
- OKX REST API via ccxt (provider primario quando EXCHANGE_PROVIDER=okx)
- Binance REST API pubblica (fallback / provider legacy)
- Caricamento da file CSV per test deterministici

TASK-1110: aggiunto fetch OKX candles via ccxt. Il provider viene letto
da settings.EXCHANGE_PROVIDER e la scelta avviene automaticamente.
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

# OKX interval mapping
OKX_INTERVALS = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "4h": "4H", "1d": "1D",
}


def _symbol_to_okx(symbol: str) -> str:
    """Convert any symbol format to OKX instId format.

    BTCUSDT -> BTC-USDT, BTCEUR -> BTC-EUR, BTC-EUR -> BTC-EUR (noop)
    """
    if "-" in symbol:
        return symbol.upper()
    # Try common quote assets
    for q in ("USDC", "USDT", "EUR", "USD", "BTC", "ETH"):
        if symbol.upper().endswith(q):
            base = symbol[:-len(q)].upper()
            return f"{base}-{q}"
    return symbol.upper()


def _symbol_to_binance(symbol: str) -> str:
    """Convert OKX instId or other format to Binance compact symbol.

    BTC-EUR -> BTCEUR, BTC/EUR -> BTCEUR, BTCUSDT -> BTCUSDT (noop)
    """
    return symbol.upper().replace("-", "").replace("/", "")


class HistoricalLoader:
    """Caricatore dati storici per backtest.

    Uso:
        loader = HistoricalLoader()
        candles = await loader.load_ohlcv("BTC-EUR", "1m", limit=100)
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
        """Carica candele OHLCV dal provider configurato.

        Usa OKX se EXCHANGE_PROVIDER=okx, altrimenti Binance.
        Se il provider primario fallisce, tenta il fallback.
        """
        try:
            from app.config import settings
            provider = settings.EXCHANGE_PROVIDER.lower()
        except Exception:
            provider = "binance"

        if provider == "okx":
            candles = await self._load_from_okx(symbol, interval, start, end, limit)
            if candles:
                return candles
            # Fallback a Binance solo se il simbolo è Binance-compatibile
            binance_sym = _symbol_to_binance(symbol)
            if "EUR" not in binance_sym:
                logger.debug("OKX fetch failed, trying Binance fallback for %s", symbol)
                return await self._load_from_binance(binance_sym, interval, start, end, limit)
            return []
        else:
            binance_sym = _symbol_to_binance(symbol)
            return await self._load_from_binance(binance_sym, interval, start, end, limit)

    # ── OKX ──────────────────────────────────────────────────────────────────

    async def _load_from_okx(
        self,
        symbol: str,
        interval: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int,
    ) -> List[Candle]:
        """Fetch OHLCV from OKX via ccxt async."""
        if interval not in OKX_INTERVALS:
            logger.warning("HistoricalLoader: interval %s not supported for OKX", interval)
            return []

        okx_sym = _symbol_to_okx(symbol)
        okx_interval = OKX_INTERVALS[interval]

        try:
            import ccxt.async_support as ccxt

            from app.config import settings
            config = {
                "enableRateLimit": True,
                "options": {"defaultType": "spot", "fetchMarkets": ["spot"]},
            }
            if settings.exchange_demo:
                config["headers"] = {"x-simulated-trading": "1"}

            exchange = ccxt.okx(config)
            # EU base URL — skip None values to avoid NoneType.replace() crash
            if "eea.okx.com" in settings.OKX_BASE_URL:
                exchange.urls["api"] = {
                    k: v.replace("www.okx.com", "eea.okx.com") if v else v
                    for k, v in exchange.urls.get("api", {}).items()
                }
            if settings.exchange_demo:
                exchange.set_sandbox_mode(True)

            try:
                since = int(start.timestamp() * 1000) if start else None
                # ccxt fetch_ohlcv returns [[ts, o, h, l, c, vol], ...]
                raw = await exchange.fetch_ohlcv(
                    symbol=okx_sym,
                    timeframe=okx_interval,
                    since=since,
                    limit=min(limit, 300),  # OKX max 300 per call
                )
            finally:
                await exchange.close()

            candles = []
            for entry in raw:
                try:
                    ts = datetime.fromtimestamp(entry[0] / 1000, tz=timezone.utc)
                    if end and ts > end:
                        continue
                    candle = Candle(
                        symbol=okx_sym,
                        open=Decimal(str(entry[1])),
                        high=Decimal(str(entry[2])),
                        low=Decimal(str(entry[3])),
                        close=Decimal(str(entry[4])),
                        volume=Decimal(str(entry[5])),
                        timestamp=ts,
                        closed=True,
                    )
                    candles.append(candle)
                except (IndexError, ValueError, TypeError) as e:
                    logger.warning("OKX OHLCV parse error for %s: %s", symbol, e)
                    continue

            if candles:
                logger.info(
                    "HistoricalLoader: loaded %d candles from OKX for %s (%s)",
                    len(candles), okx_sym, interval,
                )
            return candles

        except Exception as e:
            logger.error("Errore caricamento OHLCV da OKX: %s", e)
            return []

    # ── Binance ───────────────────────────────────────────────────────────────

    async def _load_from_binance(
        self,
        symbol: str,
        interval: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int,
    ) -> List[Candle]:
        """Fetch OHLCV from Binance public REST API."""
        if interval not in BINANCE_INTERVALS:
            raise ValueError(f"Intervallo {interval} non supportato. Usa: {list(BINANCE_INTERVALS.keys())}")

        params = f"symbol={symbol}&interval={BINANCE_INTERVALS[interval]}&limit={min(limit, 1000)}"
        if start:
            params += f"&startTime={int(start.timestamp() * 1000)}"
        if end:
            params += f"&endTime={int(end.timestamp() * 1000)}"

        url = f"{BINANCE_BASE_URL}?{params}"
        logger.debug("Fetching OHLCV from Binance: %s", url)

        try:
            req = Request(url, headers={"User-Agent": "SynthTrade/1.0"})
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error("Errore caricamento OHLCV da Binance: %s", e)
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
                logger.warning("Errore parsing entry Binance: %s, err: %s", entry[:6], e)
                continue

        if start:
            candles = [c for c in candles if c.timestamp >= start]
        if end:
            candles = [c for c in candles if c.timestamp <= end]

        if candles:
            logger.info(
                "Returning %d candles from Binance REST for %s", len(candles), symbol
            )
        return candles

    # ── CSV / Mock ────────────────────────────────────────────────────────────

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
                    logger.warning("Errore parsing riga CSV: %s, err: %s", row, e)
                    continue

        return candles

    @staticmethod
    def generate_mock_candles(
        symbol: str,
        count: int = 100,
        start_price: Decimal = Decimal("50000"),
        volatility: Decimal = Decimal("0.01"),
    ) -> List[Candle]:
        """Genera candele mock per test."""
        from random import uniform

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
