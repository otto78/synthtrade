"""Test per LongShortRatioCollector (TASK-804)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.scalping.intelligence.collectors.long_short_ratio import (
    LongShortRatioCollector,
)


class TestLongShortRatioCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        """Collettore parsa correttamente la risposta Binance."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[
            {
                "symbol": "BTCUSDT",
                "longAccount": "0.655",
                "shortAccount": "0.345",
                "timestamp": 1700000000000,
            }
        ])
        mock_response.raise_for_status = MagicMock()

        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is not None
        assert result.long_pct == Decimal("65.5")
        assert result.short_pct == Decimal("34.5")

    @pytest.mark.asyncio
    async def test_collect_empty_response(self):
        """Risposta vuota ritorna None."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[])
        mock_response.raise_for_status = MagicMock()

        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    @pytest.mark.asyncio
    async def test_collect_http_error(self):
        """Errore HTTP ritorna None."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(side_effect=Exception("API error"))

        collector = LongShortRatioCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await collector.collect("BTCUSDT")

        assert result is None

    # ── TASK-1262: score basato sul delta rispetto alla baseline recente ──
    # Il long_pct assoluto di BTC e' stazionario (~49%) e non porta informazione:
    # conta solo la variazione rispetto alla media delle letture precedenti.

    def test_ratio_to_score_more_long_than_baseline(self):
        """Long% in crescita vs baseline -> score negativo (bearish)."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("52"), baseline=48.0)
        assert score < 0

    def test_ratio_to_score_less_long_than_baseline(self):
        """Long% in calo vs baseline -> score positivo (bullish)."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("44"), baseline=48.0)
        assert score > 0

    def test_ratio_to_score_equal_to_baseline(self):
        """Long% == baseline -> score zero."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("48"), baseline=48.0)
        assert score == 0.0

    def test_ratio_to_score_ignores_absolute_level(self):
        """Un long% alto ma stabile non genera score negativo.

        TASK-1262: e' il caso reale di BTC, che sta intorno al 49% da giorni.
        Il vecchio codice lo mappava a un bias bearish costante.
        """
        score = LongShortRatioCollector.ratio_to_score(Decimal("63"), baseline=63.0)
        assert score == 0.0

    def test_ratio_to_score_no_baseline_is_neutral(self):
        """Senza baseline il contributo non e' calcolabile -> 0.0 (non crash)."""
        assert LongShortRatioCollector.ratio_to_score(Decimal("75")) == 0.0
        assert LongShortRatioCollector.ratio_to_score(Decimal("25")) == 0.0

    def test_ratio_to_score_clamped(self):
        """Raw score non supera +/- 100 anche con delta estremi."""
        score = LongShortRatioCollector.ratio_to_score(Decimal("100"), baseline=50.0)
        assert -100.0 <= score <= 100.0
        score = LongShortRatioCollector.ratio_to_score(Decimal("0"), baseline=50.0)
        assert -100.0 <= score <= 100.0

    def test_get_baseline_needs_two_readings(self):
        """Servono almeno 2 letture: con una sola la baseline sarebbe l'attuale."""
        collector = LongShortRatioCollector()
        assert collector.get_baseline() is None
        assert collector.has_baseline() is False

        collector._record_reading(50.0)
        assert collector.get_baseline() is None
        assert collector.has_baseline() is False

        collector._record_reading(52.0)
        assert collector.has_baseline() is True
        # la baseline esclude la lettura corrente: media di [50.0] = 50.0
        assert collector.get_baseline() == 50.0

    def test_get_baseline_excludes_current_reading(self):
        """La baseline usa le letture precedenti, non anche la corrente.

        Se includesse la corrente il delta sarebbe smorzato di N/(N+1) e un
        cambio di regime resterebbe invisibile.
        """
        collector = LongShortRatioCollector()
        for v in (48.0, 50.0, 52.0):
            collector._record_reading(v)
        # 52.0 e' la lettura corrente: la baseline e' media di [48.0, 50.0] = 49.0
        assert collector.get_baseline() == 49.0

        # Spike reale: deve emergere pieno, non smorzato a 1/4.
        collector._record_reading(55.0)
        assert collector.get_baseline() == 50.0
        assert LongShortRatioCollector.ratio_to_score(Decimal("55"), 50.0) == -100.0

    def test_record_reading_dedupes_identical_values(self):
        """Letture identiche consecutive non entrano nello storico.

        Il collector gira ogni 60s ma l'endpoint ha period=5m: senza dedupe ogni
        valore reale verrebbe campionato 5 volte e il lookback coprirebbe 12
        minuti invece delle 12 letture distinte (~60 min) previste dal task.
        """
        collector = LongShortRatioCollector()
        for _ in range(10):
            collector._record_reading(49.0)
        assert len(collector._history) == 1

        collector._record_reading(50.0)
        assert len(collector._history) == 2

    def test_history_respects_maxlen(self):
        """Il deque non cresce oltre il lookback configurato."""
        collector = LongShortRatioCollector()
        for i in range(40):
            collector._record_reading(float(40 + i))
        assert len(collector._history) == 12