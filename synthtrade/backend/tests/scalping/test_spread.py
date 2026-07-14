"""Test per SpreadCollector (TASK-1152).

Verifica il calcolo dello spread relativo da OKX public ticker (/market/ticker)
e la media mobile di normalizzazione. Il wiring nel weighted score è INTENZIONALMENTE
disattivato (TASK-1152): questi test coprono solo il collector + modello.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.intelligence.collectors.spread import SpreadCollector
from app.scalping.models.intelligence import SpreadSnapshot


def _mock_ticker_response(code: str, bid: str, ask: str, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value={"code": code, "data": [{"bidPx": bid, "askPx": ask}]})
    resp.raise_for_status = MagicMock()
    return resp


class TestSpreadCollector:
    @pytest.mark.asyncio
    async def test_fetch_success_normal_spread(self):
        """Spread normale -> ratio ≈ 1, non anomalo."""
        resp = _mock_ticker_response("0", "100.00", "100.05")
        collector = SpreadCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert isinstance(result, SpreadSnapshot)
        assert result.symbol == "OKB-EUR"
        assert result.bid == Decimal("100.00")
        assert result.ask == Decimal("100.05")
        assert result.spread_abs == Decimal("0.05")
        assert result.spread_pct > 0
        assert result.is_anomalous is False

    @pytest.mark.asyncio
    async def test_fetch_success_anomalous_spread_vs_rolling_avg(self):
        """Spread 3x la media mobile recente -> is_anomalous True."""
        collector = SpreadCollector()
        # Finestra riempita con spread piccoli e stabili (~0.01%)
        collector._window.extend([0.01] * (collector._window_size - 1))

        # Spread corrente ~0.05% >> media (~0.012%) -> ratio ~4x
        resp = _mock_ticker_response("0", "100.00", "100.05")
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert result is not None
        assert result.spread_pct > 0.04
        assert result.ratio_vs_avg >= 3.0
        assert result.is_anomalous is True

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        """Errore HTTP (raise_for_status) -> None, nessuna eccezione propagata."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 429"))
        collector = SpreadCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            with patch(
                "app.scalping.intelligence.collectors.spread.asyncio.sleep",
                AsyncMock(),
            ):
                result = await collector.collect("OKB-EUR")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_invalid_ticker_payload(self):
        """Payload senza data o code != '0' -> None."""
        resp = _mock_ticker_response("51001", "100.00", "100.05")
        collector = SpreadCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_zero_or_invalid_bid_ask(self):
        """bid/ask non validi (0 o None) -> None."""
        resp = _mock_ticker_response("0", "0", "100.05")
        collector = SpreadCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")
        assert result is None

    def test_rolling_average_window_size(self):
        """La finestra mobile è limitata a WINDOW_SIZE campioni (non cresce)."""
        collector = SpreadCollector(window_size=20)
        for i in range(50):
            collector._record(0.01 + i * 0.001)

        assert collector.sample_count == 20
        assert collector._window.maxlen == 20
        # La media è calcolata sugli ultimi 20 campioni
        assert abs(collector._record(0.01) - sum(collector._window) / 20) < 1e-9

    def test_first_sample_rolling_avg_equals_itself(self):
        """Con un solo campione, rolling_avg == spread_pct e ratio == 1.0."""
        collector = SpreadCollector()
        avg = collector._record(0.03)
        assert avg == 0.03
        assert collector.sample_count == 1

    def test_is_symbol_supported_always_true(self):
        """Sempre True: il ticker esiste per ogni coppia spot OKX."""
        collector = SpreadCollector()
        for symbol in ("OKB-EUR", "BTC-USDT", "ETH-EUR", "DOGE-USDT"):
            assert collector.is_symbol_supported(symbol) is True
