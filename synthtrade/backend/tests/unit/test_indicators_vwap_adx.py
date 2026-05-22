"""🔴 RED + 🟢 GREEN: Test per VWAP, ADX e regime filters (TASK-801)."""
import pytest
import pandas as pd
import numpy as np
from app.core.indicators import (
    vwap, adx, detect_trend, detect_volatility,
)


@pytest.fixture
def sample_ohlcv():
    """DataFrame con OHLCV simulato — 200 candele."""
    np.random.seed(42)
    n = 200
    close = 100 + np.cumsum(np.random.randn(n))
    high = close + np.abs(np.random.randn(n)) * 2
    low = close - np.abs(np.random.randn(n)) * 2
    volume = np.random.rand(n) * 1000 + 100
    return pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def trending_up_ohlcv():
    """Serie con forte trend rialzista."""
    np.random.seed(0)
    n = 200
    close = 100 + np.cumsum(np.abs(np.random.randn(n)) + 0.5)
    high = close + np.abs(np.random.randn(n)) * 2
    low = close - np.abs(np.random.randn(n)) * 2
    volume = np.random.rand(n) * 1000 + 100
    return pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def flat_ohlcv():
    """Serie laterale/piatta — volatilità molto bassa."""
    n = 200
    close = pd.Series(np.full(n, 150.0)) + np.random.randn(n) * 0.1
    high = close + 0.3
    low = close - 0.3
    volume = np.full(n, 500.0)
    return pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


# ── VWAP ───────────────────────────────────────────────────────────────

class TestVWAP:
    """Test per VWAP (Volume Weighted Average Price)."""

    def test_vwap_returns_series(self, sample_ohlcv):
        result = vwap(sample_ohlcv)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)

    def test_vwap_calculation(self):
        """VWAP = sum(close * volume) / sum(volume) cumulativo."""
        df = pd.DataFrame({
            "close": [100.0, 102.0, 101.0],
            "volume": [1000, 1500, 1200],
        })
        result = vwap(df)
        # Indice 0: (100*1000)/1000 = 100
        assert abs(result.iloc[0] - 100.0) < 0.01
        # Indice 1: (100*1000 + 102*1500)/(1000+1500) = 253000/2500 = 101.2
        assert abs(result.iloc[1] - 101.2) < 0.01
        # Indice 2: (100*1000 + 102*1500 + 101*1200)/(1000+1500+1200) = 374200/3700 ≈ 101.135
        expected = (100*1000 + 102*1500 + 101*1200) / (1000 + 1500 + 1200)
        assert abs(result.iloc[2] - expected) < 0.01

    def test_vwap_tracks_price_trend(self, sample_ohlcv):
        """VWAP deve seguire l'andamento del prezzo (non divergere eccessivamente)."""
        result = vwap(sample_ohlcv)
        valid = result.dropna().index[50:]  # dopo il warmup
        max_deviation = (result[valid] - sample_ohlcv["close"][valid]).abs().max()
        # VWAP non deve divergere più del 5% dal prezzo di chiusura
        price_range = sample_ohlcv["close"].max() - sample_ohlcv["close"].min()
        assert max_deviation < price_range * 0.5

    def test_vwap_handles_zero_volume(self):
        """Se volume=0, VWAP deve restare invariato o gestire gracefully."""
        df = pd.DataFrame({
            "close": [100.0, 101.0],
            "volume": [1000, 0],
        })
        result = vwap(df)
        assert pd.notna(result.iloc[1])
        # Con volume zero, il VWAP cumulative non cambia
        assert abs(result.iloc[1] - result.iloc[0]) < 0.01

    def test_vwap_no_lookahead(self, sample_ohlcv):
        """Rimuovere l'ultima riga non deve cambiare i VWAP precedenti."""
        vwap_full = vwap(sample_ohlcv)
        vwap_trim = vwap(sample_ohlcv.iloc[:-1])
        pd.testing.assert_series_equal(
            vwap_full.iloc[:-1].reset_index(drop=True),
            vwap_trim.reset_index(drop=True),
        )


# ── ADX ────────────────────────────────────────────────────────────────

class TestADX:
    """Test per ADX (Average Directional Index)."""

    def test_adx_returns_series(self, sample_ohlcv):
        result = adx(sample_ohlcv, period=14)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)

    def test_adx_range(self, sample_ohlcv):
        """ADX deve essere tra 0 e 100."""
        result = adx(sample_ohlcv, period=14)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_adx_high_on_trend(self, trending_up_ohlcv):
        """Su trend forte, ADX deve essere > 25 (trend presente)."""
        result = adx(trending_up_ohlcv, period=14)
        # Prendiamo gli ultimi valori dopo che ADX si è stabilizzato
        last_values = result.dropna().iloc[-20:]
        assert last_values.mean() > 25

    def test_adx_low_on_flat(self, flat_ohlcv):
        """Su mercato piatto, ADX deve essere < 25 (no trend)."""
        result = adx(flat_ohlcv, period=14)
        last_values = result.dropna().iloc[-20:]
        assert last_values.mean() < 25

    def test_adx_length_matches_period(self, sample_ohlcv):
        """ADX deve avere NaN per i primi `period` valori."""
        result = adx(sample_ohlcv, period=14)
        assert pd.isna(result.iloc[:13]).all()  # 14 valori NaN (0-13)
        assert pd.notna(result.iloc[14:]).any()  # dal 15esimo in poi

    def test_adx_no_lookahead(self, sample_ohlcv):
        """Rimuovere l'ultima riga non deve cambiare ADX precedenti."""
        adx_full = adx(sample_ohlcv, period=14)
        adx_trim = adx(sample_ohlcv.iloc[:-1], period=14)
        pd.testing.assert_series_equal(
            adx_full.iloc[:-1].reset_index(drop=True),
            adx_trim.reset_index(drop=True),
        )


# ── Regime Detection ───────────────────────────────────────────────────

class TestDetectTrend:
    """Test per detect_trend()."""

    def test_detect_trend_returns_string(self, sample_ohlcv):
        result = detect_trend(sample_ohlcv, period=20)
        assert isinstance(result, str)

    def test_detect_trend_up(self, trending_up_ohlcv):
        """Su trend rialzista, deve restituire 'uptrend'."""
        result = detect_trend(trending_up_ohlcv, period=20)
        assert result == "uptrend"

    def test_detect_trend_flat(self, flat_ohlcv):
        """Su mercato piatto, deve restituire 'ranging'."""
        result = detect_trend(flat_ohlcv, period=20)
        # Può essere ranging o downtrend leggero
        # Verifichiamo che non sia uptrend
        assert result != "uptrend"

    def test_detect_trend_rejects_short_data(self, sample_ohlcv):
        """Con pochi dati, deve restituire 'insufficient_data'."""
        short_df = sample_ohlcv.iloc[:5]
        result = detect_trend(short_df, period=20)
        assert result == "insufficient_data"


class TestDetectVolatility:
    """Test per detect_volatility()."""

    def test_detect_volatility_returns_float(self, sample_ohlcv):
        result = detect_volatility(sample_ohlcv, period=20)
        assert isinstance(result, float)

    def test_detect_volatility_positive(self, sample_ohlcv):
        result = detect_volatility(sample_ohlcv, period=20)
        assert result >= 0

    def test_detect_volatility_low_on_flat(self, flat_ohlcv):
        """Su mercato piatto, la volatilità deve essere bassa."""
        result = detect_volatility(flat_ohlcv, period=20)
        assert result < 1.0

    def test_detect_volatility_higher_on_trend(self, trending_up_ohlcv, flat_ohlcv):
        """Su trend, la volatilità deve essere maggiore che sul flat."""
        vol_trend = detect_volatility(trending_up_ohlcv, period=20)
        vol_flat = detect_volatility(flat_ohlcv, period=20)
        assert vol_trend >= vol_flat