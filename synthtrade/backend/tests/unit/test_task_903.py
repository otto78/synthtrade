"""Tests for RegimeDetector TASK-903: isteresi K candele."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.scalping.engine.regime_detector import REGIME_HYSTERESIS_K, RegimeDetector
from app.scalping.models.market import Candle, MarketRegime


def _make_candles(
    closes: list[float],
    spread: float = 10.0,
) -> list[Candle]:
    """Crea candele 1m con spread controllato."""
    now = datetime.now(timezone.utc)
    return [
        Candle(
            symbol="BTC-EUR",
            open=Decimal(str(c)),
            high=Decimal(str(c + spread)),
            low=Decimal(str(c - spread)),
            close=Decimal(str(c)),
            volume=Decimal("100"),
            timestamp=now,
        )
        for c in closes
    ]


def _ranging_candles(n: int = 25, base: float = 50000.0) -> list[Candle]:
    """Candele con prezzo stabile → regime 'ranging'."""
    closes = [base] * n
    return _make_candles(closes, spread=5.0)


def _trending_up_candles(n: int = 25, start: float = 50000.0) -> list[Candle]:
    """Candele in uptrend → regime 'trending_up' (price_change > 0.3%)."""
    step = start * 0.0005  # 0.05% per candela → ~1.25% su 25 candele
    closes = [start + i * step for i in range(n)]
    return _make_candles(closes, spread=5.0)


def _trending_down_candles(n: int = 25, start: float = 50000.0) -> list[Candle]:
    """Candele in downtrend → regime 'trending_down'."""
    step = start * 0.0005
    closes = [start - i * step for i in range(n)]
    return _make_candles(closes, spread=5.0)


def _volatile_candles(n: int = 25, base: float = 50000.0) -> list[Candle]:
    """Candele con alta volatilità → regime 'volatile'."""
    now = datetime.now(timezone.utc)
    candles = []
    for i in range(n):
        c = base + (i % 3 - 1) * 100
        spread = base * 0.015  # 1.5% spread → volatility_ratio > 0.01
        candles.append(Candle(
            symbol="BTC-EUR",
            open=Decimal(str(c)),
            high=Decimal(str(c + spread)),
            low=Decimal(str(c - spread)),
            close=Decimal(str(c)),
            volume=Decimal("100"),
            timestamp=now,
        ))
    return candles


class TestRegimeDetectorHysteresis:
    """TASK-903: isteresi K candele su regime detector."""

    def test_first_call_immediate_commit(self):
        """Prima chiamata → commit immediato del candidato."""
        det = RegimeDetector(k=3)
        candles = _ranging_candles()
        result = det.detect(candles)
        assert result.regime == "ranging"
        assert det.committed_regime == "ranging"
        assert det.pending_regime is None
        assert det.pending_count == 0

    def test_stable_regime_no_change(self):
        """Candidato uguale al committed → nessun pending, restituisce committed."""
        det = RegimeDetector(k=3)
        candles = _ranging_candles()
        det.detect(candles)  # commit ranging
        result = det.detect(candles)  # stesse candele
        assert result.regime == "ranging"
        assert det.pending_regime is None
        assert det.pending_count == 0

    def test_new_candidate_starts_pending(self):
        """Nuovo candidato per 1 candela → pending_count=1, committed invariato."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())  # commit ranging
        result = det.detect(_trending_up_candles())  # 1st trending_up
        assert result.regime == "ranging"  # ancora committed
        assert det.pending_regime == "trending_up"
        assert det.pending_count == 1

    def test_new_candidate_before_k_resets_on_change(self):
        """Candidato cambia prima di K → reset counter."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())  # commit ranging
        det.detect(_trending_up_candles())  # pending: trending_up count=1
        det.detect(_trending_down_candles())  # nuovo candidato → reset
        assert det.pending_regime == "trending_down"
        assert det.pending_count == 1
        assert det.committed_regime == "ranging"

    def test_candidate_k_consecutive_commits(self):
        """Stesso candidato per K candele → commit del nuovo regime."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())  # commit ranging
        det.detect(_trending_up_candles())  # pending: trending_up count=1
        det.detect(_trending_up_candles())  # pending: trending_up count=2
        result = det.detect(_trending_up_candles())  # count=3 → commit
        assert result.regime == "trending_up"
        assert det.committed_regime == "trending_up"
        assert det.pending_regime is None
        assert det.pending_count == 0

    def test_k_minus_one_not_committed(self):
        """K-1 candele non bastano per commit."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())  # commit ranging
        det.detect(_trending_up_candles())  # count=1
        det.detect(_trending_up_candles())  # count=2
        result = det.detect(_ranging_candles())  # cambio → reset, ancora ranging
        assert result.regime == "ranging"
        assert det.committed_regime == "ranging"

    def test_k_equals_one_immediate_change(self):
        """K=1 → ogni cambio candidato viene committato immediatamente."""
        det = RegimeDetector(k=1)
        det.detect(_ranging_candles())  # commit ranging
        result = det.detect(_trending_up_candles())  # count=1=K → commit
        assert result.regime == "trending_up"

    def test_k_equals_five(self):
        """K=5 → servono 5 candele consecutive."""
        det = RegimeDetector(k=5)
        det.detect(_ranging_candles())  # commit ranging
        for i in range(4):
            result = det.detect(_trending_up_candles())
            assert result.regime == "ranging"
            assert det.pending_count == i + 1
        result = det.detect(_trending_up_candles())  # 5th → commit
        assert result.regime == "trending_up"

    def test_pending_regime_property(self):
        """pending_regime restituisce il candidato corrente."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())
        assert det.pending_regime is None
        det.detect(_trending_up_candles())
        assert det.pending_regime == "trending_up"
        det.detect(_trending_up_candles())
        assert det.pending_regime == "trending_up"
        det.detect(_trending_up_candles())  # commit
        assert det.pending_regime is None

    def test_multiple_transitions(self):
        """Transizioni multiple: ranging → trending_up → volatile."""
        det = RegimeDetector(k=2)
        det.detect(_ranging_candles())  # commit ranging
        # ranging → trending_up
        det.detect(_trending_up_candles())
        det.detect(_trending_up_candles())  # commit trending_up
        assert det.committed_regime == "trending_up"
        # trending_up → volatile
        det.detect(_volatile_candles())
        det.detect(_volatile_candles())  # commit volatile
        assert det.committed_regime == "volatile"

    def test_transitions_through_pending(self):
        """Transizione con conteggio intermedio visibile."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())  # commit ranging
        # 1st candidate
        det.detect(_trending_up_candles())
        assert det.pending_count == 1
        # 2nd candidate
        det.detect(_trending_up_candles())
        assert det.pending_count == 2
        # 3rd candidate → commit
        result = det.detect(_trending_up_candles())
        assert det.pending_count == 0
        assert result.regime == "trending_up"

    def test_stays_committed_during_pending(self):
        """Durante pending, committed non cambia e il risultato è committed."""
        det = RegimeDetector(k=3)
        det.detect(_ranging_candles())  # commit ranging
        r1 = det.detect(_trending_up_candles())  # pending
        r2 = det.detect(_trending_up_candles())  # pending
        assert r1.regime == "ranging"
        assert r2.regime == "ranging"
        assert det.committed_regime == "ranging"

    def test_default_k_matches_constant(self):
        """Default K corrisponde a REGIME_HYSTERESIS_K."""
        det = RegimeDetector()
        assert det._k == REGIME_HYSTERESIS_K

    def test_only_20_candles_used(self):
        """Regime basato sulle ultime 20 candele, non tutte."""
        det = RegimeDetector(k=1)
        # 20 ranging + 20 trending_up = 40 candles
        # L'ultime 20 sono tutte trending_up
        candles = _ranging_candles(n=20) + _trending_up_candles(n=20)
        result = det.detect(candles)
        assert result.regime == "trending_up"

    def test_fewer_than_20_candles_ranging(self):
        """< 20 candele ma >= 5 → ranging fallback (no isteresi su fallback)."""
        det = RegimeDetector(k=3)
        result = det.detect(_ranging_candles(n=10))
        assert result.regime == "ranging"
        assert result.confidence == 0.3
