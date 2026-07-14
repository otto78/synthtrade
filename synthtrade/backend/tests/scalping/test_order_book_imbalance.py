"""Test per OrderBookImbalanceCollector (TASK-1151).

Verifica il calcolo dell'imbalance da OKX public market data (/market/books)
e il wiring nel SignalScoreEngine. Funziona su QUALSIASI coppia spot OKX
(incluso OKB-EUR) perche' non dipende da un mercato futures.
"""

from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.intelligence.collectors.order_book_imbalance import (
    OrderBookImbalanceCollector,
)
from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
from app.scalping.models.intelligence import OrderBookImbalance


def _mock_response(code: str, data, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value={"code": code, "data": data})
    resp.raise_for_status = MagicMock()
    return resp


class TestOrderBookImbalanceCollector:
    @pytest.mark.asyncio
    async def test_fetch_success_balanced_book(self):
        """Bid e ask bilanciati -> imbalance ≈ 0."""
        book = {"bids": [["100.0", "10.0"]], "asks": [["100.1", "10.0"]]}
        resp = _mock_response("0", [book])
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert isinstance(result, OrderBookImbalance)
        assert result.symbol == "OKB-EUR"
        assert abs(result.imbalance) < 1e-6

    @pytest.mark.asyncio
    async def test_collect_normalizes_compact_symbol_to_okx_instid(self):
        """Regression (TASK-1151): lo stream passa self.symbol in formato
        uppercase-senza-dash (es. OKBEUR). Il collector DEVE normalizzarlo in
        OKB-EUR prima della chiamata a /market/books, altrimenti OKX ritorna
        code!=0 e il collector torna None in produzione (bug silenzioso)."""
        book = {"bids": [["100.0", "10.0"]], "asks": [["100.1", "10.0"]]}
        resp = _mock_response("0", [book])

        fake = AsyncMock(return_value=resp)
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", fake):
            result = await collector.collect("OKBEUR")

        assert result is not None
        assert fake.call_args.kwargs["params"]["instId"] == "OKB-EUR"
        assert result.symbol == "OKB-EUR"

    @pytest.mark.asyncio
    async def test_fetch_success_bid_heavy(self):
        """Molto piu' liquidita' bid -> imbalance vicino a +1."""
        book = {
            "bids": [["100.0", "1000.0"], ["99.9", "1000.0"], ["99.8", "1000.0"]],
            "asks": [["100.1", "1.0"]],
        }
        resp = _mock_response("0", [book])
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert result is not None
        assert result.imbalance > 0.99

    @pytest.mark.asyncio
    async def test_fetch_success_ask_heavy(self):
        """Molto piu' liquidita' ask -> imbalance vicino a -1."""
        book = {
            "bids": [["100.0", "1.0"]],
            "asks": [["100.1", "1000.0"], ["100.2", "1000.0"], ["100.3", "1000.0"]],
        }
        resp = _mock_response("0", [book])
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert result is not None
        assert result.imbalance < -0.99

    @pytest.mark.asyncio
    async def test_fetch_empty_book(self):
        """Order book vuoto (bids/asks vuoti) -> None, nessuna eccezione."""
        book = {"bids": [], "asks": []}
        resp = _mock_response("0", [book])
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_empty_payload(self):
        """Risposta senza data -> None."""
        resp = _mock_response("0", [])
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_nonzero_code(self):
        """code diverso da '0' -> None."""
        resp = _mock_response("51001", [{"bids": [], "asks": []}])
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            result = await collector.collect("OKB-EUR")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        """Errore HTTP (raise_for_status) -> None, nessuna eccezione propagata."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 429"))
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            with patch(
                "app.scalping.intelligence.collectors.order_book_imbalance.asyncio.sleep",
                AsyncMock(),
            ):
                result = await collector.collect("OKB-EUR")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_http_status_error(self):
        """Status 4xx/5xx (response.json fallisce) -> None, nessuna eccezione."""
        resp = MagicMock()
        resp.status_code = 500
        resp.raise_for_status = MagicMock(side_effect=Exception("500 Server Error"))
        collector = OrderBookImbalanceCollector()
        with patch("httpx.AsyncClient.get", AsyncMock(return_value=resp)):
            with patch(
                "app.scalping.intelligence.collectors.order_book_imbalance.asyncio.sleep",
                AsyncMock(),
            ):
                result = await collector.collect("OKB-EUR")

        assert result is None

    def test_is_symbol_supported_always_true(self):
        """Sempre True: l'order book esiste per ogni coppia spot OKX."""
        collector = OrderBookImbalanceCollector()
        for symbol in ("OKB-EUR", "BTC-USDT", "ETH-EUR", "DOGE-USDT"):
            assert collector.is_symbol_supported(symbol) is True

    @pytest.mark.parametrize(
        "imbalance,expected_score",
        [
            (-1.0, -100.0),
            (-0.5, -50.0),
            (0.0, 0.0),
            (0.5, 50.0),
            (1.0, 100.0),
        ],
    )
    def test_imbalance_to_score_clamped(self, imbalance, expected_score):
        """Score = imbalance * 100, clampato a [-100, +100]."""
        score = OrderBookImbalanceCollector.imbalance_to_score(imbalance)
        assert score == expected_score
        assert -100.0 <= score <= 100.0

    def test_imbalance_to_score_beyond_clamp(self):
        """Valori oltre i limiti vengono clampati."""
        assert OrderBookImbalanceCollector.imbalance_to_score(5.0) == 100.0
        assert OrderBookImbalanceCollector.imbalance_to_score(-5.0) == -100.0


class TestOrderBookImbalanceEngineWiring:
    @pytest.mark.asyncio
    async def test_engine_includes_order_book_imbalance(self):
        """L'engine usa il collector OBI e lo include nel breakdown."""
        engine = SignalScoreEngine(symbol="OKB-EUR", threshold=30.0)

        obi = OrderBookImbalance(
            symbol="OKB-EUR",
            bid_depth=Decimal("1000"),
            ask_depth=Decimal("500"),
            imbalance=0.33,
            timestamp=datetime.now(timezone.utc),
        )
        engine._order_book_imbalance.collect = AsyncMock(return_value=obi)

        # Disattiva gli altri collector per isolare il contributo OBI
        engine._funding_rate.collect = AsyncMock(return_value=None)
        engine._open_interest.collect = AsyncMock(return_value=None)
        engine._long_short.collect = AsyncMock(return_value=None)
        engine._fear_greed.collect = AsyncMock(return_value=None)
        engine._sentiment.collect = AsyncMock(return_value=None)
        engine._whale.collect = AsyncMock(return_value=None)
        engine._onchain.collect = AsyncMock(return_value=None)

        score = await engine.compute()

        assert "order_book_imbalance" in score.breakdown
        assert score.breakdown["order_book_imbalance"] == pytest.approx(33.0, abs=0.1)
