import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


# ── Helpers ───────────────────────────────────────────────────────────

def make_candles(n: int, start_price: float = 100.0) -> list:
    """Genera n candele OHLCV in formato ccxt (lista di liste)."""
    base_ts = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    candles = []
    price = start_price
    for i in range(n):
        ts = base_ts + i * 5 * 60 * 1000  # 5 minuti
        candles.append([ts, price, price * 1.001, price * 0.999, price, 1000.0])
        price += 0.1
    return candles


def make_cached_rows(n: int, start_price: float = 100.0) -> list[dict]:
    """Genera n righe in formato Supabase (lista di dict)."""
    base_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = start_price
    for i in range(n):
        ts = base_ts.replace(minute=0, second=0, microsecond=0)
        ts = datetime.fromtimestamp(
            base_ts.timestamp() + i * 5 * 60, tz=timezone.utc
        )
        rows.append({
            "ts": ts.isoformat(),
            "open": price, "high": price * 1.001,
            "low": price * 0.999, "close": price, "volume": 1000.0,
        })
        price += 0.1
    return rows


# ── Test: cache vuota → fetch Binance ────────────────────────────────

def test_empty_cache_fetches_from_binance():
    candles = make_candles(100)

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.execute.return_value.data = []

    with patch("app.core.market_data.get_supabase", return_value=mock_db), \
         patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ohlcv.return_value = candles

        from app.core.market_data import fetch_ohlcv
        df = fetch_ohlcv("BTC/USDT", "5m", days=1)

    assert not df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_empty_cache_upserts_to_supabase():
    candles = make_candles(50)

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.execute.return_value.data = []

    with patch("app.core.market_data.get_supabase", return_value=mock_db), \
         patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ohlcv.return_value = candles

        from app.core.market_data import fetch_ohlcv
        fetch_ohlcv("BTC/USDT", "5m", days=1)

    mock_db.table.return_value.upsert.assert_called_once()


# ── Test: cache parziale → fetch solo delta ───────────────────────────

def test_partial_cache_fetches_only_delta():
    cached = make_cached_rows(50)
    new_candles = make_candles(10, start_price=105.0)

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.execute.return_value.data = cached

    with patch("app.core.market_data.get_supabase", return_value=mock_db), \
         patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ohlcv.return_value = new_candles

        from app.core.market_data import fetch_ohlcv
        df = fetch_ohlcv("BTC/USDT", "5m", days=1)

    # Binance chiamato una volta sola (solo il delta)
    assert mock_ex.fetch_ohlcv.call_count == 1


# ── Test: output DataFrame ────────────────────────────────────────────

def test_output_has_correct_columns():
    candles = make_candles(20)

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.execute.return_value.data = []

    with patch("app.core.market_data.get_supabase", return_value=mock_db), \
         patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ohlcv.return_value = candles

        from app.core.market_data import fetch_ohlcv
        df = fetch_ohlcv("BTC/USDT", "5m", days=1)

    assert set(df.columns) == {"open", "high", "low", "close", "volume"}


def test_output_no_duplicate_timestamps():
    candles = make_candles(30)

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.execute.return_value.data = []

    with patch("app.core.market_data.get_supabase", return_value=mock_db), \
         patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ohlcv.return_value = candles

        from app.core.market_data import fetch_ohlcv
        df = fetch_ohlcv("BTC/USDT", "5m", days=1)

    assert df.index.duplicated().sum() == 0


def test_output_dtypes_are_float():
    candles = make_candles(20)

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.execute.return_value.data = []

    with patch("app.core.market_data.get_supabase", return_value=mock_db), \
         patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ohlcv.return_value = candles

        from app.core.market_data import fetch_ohlcv
        df = fetch_ohlcv("BTC/USDT", "5m", days=1)

    for col in df.columns:
        assert df[col].dtype == float


# ── Test: get_current_price ───────────────────────────────────────────

def test_get_current_price_returns_float():
    with patch("app.core.market_data.exchange") as mock_ex:
        mock_ex.fetch_ticker.return_value = {"last": "62000.50"}

        from app.core.market_data import get_current_price
        price = get_current_price("BTC/USDT")

    assert isinstance(price, float)
    assert price == 62000.50
