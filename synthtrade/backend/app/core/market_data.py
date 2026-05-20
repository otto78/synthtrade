import ccxt
import pandas as pd
from datetime import datetime, timedelta, timezone
from app.db.supabase_client import get_supabase
from app.config import settings
from app.core.exchange_factory import get_exchange

# Inizializzazione exchange via ExchangeFactory (TASK-431)
# La factory gestisce automaticamente key/URL in base a TRADING_MODE
exchange = get_exchange()

# Configurazione aggiuntiva per Spot Market Data
exchange.options["defaultType"] = "spot"

# Override URL per Spot Testnet (la sandbox mode non basta per spot)
if settings.TRADING_MODE == 'test':
    vision_url = "https://testnet.binance.vision/api/v3"
    exchange.urls["api"] = {
        "public": vision_url,
        "private": vision_url,
        "v3": vision_url,
        "v1": vision_url,
        "sapi": vision_url,
        "fapiPublic": vision_url,
        "fapiPrivate": vision_url,
        "dapiPublic": vision_url,
        "dapiPrivate": vision_url,
    }

OHLCV_COLS = ["open", "high", "low", "close", "volume"]


def fetch_ohlcv(pair: str, timeframe: str, days: int = 180) -> pd.DataFrame:
    db = get_supabase()
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    cached = (db.table("ohlcv_cache")
               .select("*")
               .eq("pair", pair)
               .eq("timeframe", timeframe)
               .gte("ts", since.isoformat())
               .order("ts")
               .execute())

    cached_df = _rows_to_df(cached.data) if cached.data else pd.DataFrame()

    fetch_since = (
        int(cached_df.index[-1].timestamp() * 1000) + 1
        if not cached_df.empty
        else int(since.timestamp() * 1000)
    )

    new_candles = _fetch_paginated(pair, timeframe, fetch_since)

    if new_candles:
        rows = [
            {"pair": pair, "timeframe": timeframe,
             "ts": datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc).isoformat(),
             "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]}
            for c in new_candles
        ]
        db.table("ohlcv_cache").upsert(rows).execute()

    new_df = _candles_to_df(new_candles) if new_candles else pd.DataFrame()
    combined = pd.concat([cached_df, new_df])
    return combined[~combined.index.duplicated(keep="last")].sort_index()


def get_current_price(pair: str) -> float:
    return float(exchange.fetch_ticker(pair)["last"])


def _fetch_paginated(pair: str, timeframe: str, since_ms: int) -> list:
    all_candles = []
    while True:
        batch = exchange.fetch_ohlcv(pair, timeframe, since=since_ms, limit=1000)
        if not batch:
            break
        all_candles.extend(batch)
        since_ms = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    return all_candles


def _rows_to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df["ts"])
    df.index.name = "timestamp"
    return df[OHLCV_COLS].astype(float)


def _candles_to_df(candles: list) -> pd.DataFrame:
    df = pd.DataFrame(candles, columns=["timestamp"] + OHLCV_COLS)
    df.index = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.index.name = "timestamp"
    return df[OHLCV_COLS].astype(float)
