"""Test per i modelli Pydantic dell'Intelligence Layer (TASK-804)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

# timezone-aware helper
_now = lambda: datetime.now(timezone.utc)
from app.scalping.models.intelligence import (
    CVDData,
    FearGreedData,
    FundingRate,
    LongShortRatio,
    MarketIntelSnapshot,
    OpenInterest,
    SignalScore,
    OnChainData,
    SentimentData,
    WhaleData,
)


class TestFundingRate:
    def test_valid_funding_rate(self):
        """Creazione valida di FundingRate."""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        fr = FundingRate(symbol="BTCUSDT", rate=Decimal("0.0001"), timestamp=dt)
        assert fr.symbol == "BTCUSDT"
        assert fr.rate == Decimal("0.0001")
        assert fr.timestamp == dt
        assert fr.next_funding_time is None
        assert fr.collected_at is not None

    def test_frozen(self):
        """I modelli sono frozen (immutabili)."""
        dt = _now()
        fr = FundingRate(symbol="BTCUSDT", rate=Decimal("0.0001"), timestamp=dt)
        with pytest.raises(ValidationError, match="frozen_instance"):
            fr.symbol = "ETHUSDT"

    def test_missing_required(self):
        """Campi obbligatori non possono mancare."""
        with pytest.raises(ValidationError):
            # Usiamo model_validate con un dict per evitare errori di tipo statici nel costruttore
            FundingRate.model_validate({"rate": Decimal("0.0001"), "timestamp": _now()})


class TestOpenInterest:
    def test_valid_open_interest(self):
        oi = OpenInterest(
            symbol="BTCUSDT",
            value_usd=Decimal("1000000000"),
            timestamp=_now(),
        )
        assert oi.value_usd == Decimal("1000000000")


class TestLongShortRatio:
    def test_valid_ratio(self):
        lr = LongShortRatio(
            symbol="BTCUSDT",
            long_pct=Decimal("65.5"),
            short_pct=Decimal("34.5"),
            timestamp=_now(),
        )
        assert lr.long_pct == Decimal("65.5")
        assert lr.short_pct == Decimal("34.5")

    def test_ratio_property(self):
        """La proprietà ratio restituisce long/short."""
        lr = LongShortRatio(
            symbol="BTCUSDT",
            long_pct=Decimal("60"),
            short_pct=Decimal("40"),
            timestamp=_now(),
        )
        assert lr.ratio == 1.5

    def test_invalid_percentages(self):
        """Percentuali fuori range 0-100 sollevano errore."""
        with pytest.raises(ValidationError):
            LongShortRatio(
                symbol="BTCUSDT",
                long_pct=Decimal("150"),
                short_pct=Decimal("-10"),
                timestamp=_now(),
            )


class TestCVDData:
    def test_valid_cvd(self):
        cvd = CVDData(
            symbol="BTCUSDT",
            cvd=Decimal("1500.50"),
            delta=Decimal("25.30"),
            trend="rising",
            timestamp=_now(),
        )
        assert cvd.cvd == Decimal("1500.50")
        assert cvd.trend == "rising"

    def test_cvd_defaults(self):
        """delta e trend hanno valori di default."""
        cvd = CVDData(
            symbol="BTCUSDT",
            cvd=Decimal("1000"),
            timestamp=_now(),
        )
        assert cvd.delta == Decimal("0")
        assert cvd.trend is None


class TestFearGreedData:
    def test_valid_fear_greed(self):
        fg = FearGreedData(value=25, timestamp=_now())
        assert fg.value == 25

    def test_extreme_values(self):
        """Valori estremi 0 e 100 sono validi."""
        fg0 = FearGreedData(value=0, timestamp=_now())
        fg100 = FearGreedData(value=100, timestamp=_now())
        assert fg0.value == 0
        assert fg100.value == 100

    def test_out_of_range(self):
        """Valori fuori 0-100 sollevano errore."""
        with pytest.raises(ValidationError):
            FearGreedData(value=150, timestamp=_now())

    def test_with_label(self):
        fg = FearGreedData(
            value=85, label="Extreme Greed", timestamp=_now()
        )
        assert fg.label == "Extreme Greed"


class TestOnChainData:
    def test_valid_onchain(self):
        data = {
            "symbol": "BTCUSDT",
            "exchange_net_flow": Decimal("-500.5"),
            "active_addresses": 600000,
            "transaction_count": 350000,
            "timestamp": _now()
        }
        oc = OnChainData.model_validate(data)
        assert oc.symbol == "BTCUSDT"
        assert oc.exchange_net_flow == Decimal("-500.5")
        assert oc.active_addresses == 600000


class TestSentimentData:
    def test_valid_sentiment(self):
        data = {
            "symbol": "BTCUSDT",
            "score": 0.75,
            "news_count": 15,
            "top_headlines": ["Bullish breakout", "Adoption surge"]
        }
        sd = SentimentData.model_validate(data)
        assert sd.symbol == "BTCUSDT"
        assert sd.score == 0.75
        assert len(sd.top_headlines) == 2


class TestWhaleData:
    def test_valid_whale(self):
        data = {
            "symbol": "BTCUSDT",
            "whale_transaction_count": 5,
            "large_transfer_volume": Decimal("1000.0"),
            "recent_whale_activity": True,
            "timestamp": _now()
        }
        wd = WhaleData.model_validate(data)
        assert wd.symbol == "BTCUSDT"
        assert wd.whale_transaction_count == 5
        assert wd.recent_whale_activity is True


class TestSignalScore:
    def test_valid_score_bullish(self):
        score = SignalScore(total=65.0, bias="bullish", tradeable=True, symbol="BTCUSDT")
        assert score.total == 65.0
        assert score.bias == "bullish"
        assert score.tradeable is True

    def test_valid_score_bearish(self):
        score = SignalScore(total=-45.0, bias="bearish", tradeable=True, symbol="BTCUSDT")
        assert score.total == -45.0
        assert score.bias == "bearish"

    def test_neutral_not_tradeable(self):
        score = SignalScore(total=10.0, bias="neutral", tradeable=False, symbol="BTCUSDT")
        assert score.tradeable is False

    def test_score_limits(self):
        """Score fuori -100..+100 solleva errore."""
        with pytest.raises(ValidationError):
            SignalScore(total=150.0, symbol="BTCUSDT")

    def test_invalid_bias(self):
        """Bias deve essere bullish|bearish|neutral."""
        with pytest.raises(ValidationError):
            SignalScore(total=50.0, bias="invalid", symbol="BTCUSDT")

    def test_breakdown_dict(self):
        score = SignalScore(
            total=50.0,
            bias="bullish",
            symbol="BTCUSDT",
            breakdown={"funding_rate": 20.0, "cvd": 15.0, "fear_greed": 15.0},
        )
        assert len(score.breakdown) == 3
        assert score.breakdown["funding_rate"] == 20.0


class TestMarketIntelSnapshot:
    def test_valid_snapshot(self):
        snapshot = MarketIntelSnapshot(symbol="BTCUSDT")
        assert snapshot.symbol == "BTCUSDT"
        assert snapshot.funding_rate is None
        assert snapshot.signal_score is None

    def test_snapshot_with_data(self):
        fr = FundingRate(
            symbol="BTCUSDT",
            rate=Decimal("0.01"),
            timestamp=_now(),
        )
        score = SignalScore(total=40.0, bias="bullish", symbol="BTCUSDT")
        snapshot = MarketIntelSnapshot(
            symbol="BTCUSDT",
            funding_rate=fr,
            signal_score=score,
        )
        assert snapshot.funding_rate is not None
        assert snapshot.funding_rate.rate == Decimal("0.01")
        assert snapshot.signal_score is not None
        assert snapshot.signal_score.total == 40.0