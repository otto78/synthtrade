"""Test TASK-1154 — SentimentCollector fallback robusto.

Copre: ordine di priorita', fallback a NewsAPI/RSS, fallback neutrale quando
tutto fallisce, cache 5 min (anti rate-limit) e log compatto su errori DNS
ripetuti (senza stack trace).
"""
import logging
from unittest.mock import MagicMock, patch

import pytest

from app.scalping.intelligence.collectors.sentiment import SentimentCollector
from app.scalping.models.intelligence import SentimentData


SYMBOL = "BTC-EUR"


def _json_response(status_code, payload):
    m = MagicMock()
    m.status_code = status_code
    m.json = MagicMock(return_value=payload)
    m.text = ""
    return m


def _rss_response(text):
    m = MagicMock()
    m.status_code = 200
    m.text = text
    return m


RSS_TEXT = (
    "<rss><channel>"
    "<item><title>ETH bear crash fears spread</title></item>"
    "<item><title>solana bull rally continues</title></item>"
    "</channel></rss>"
)


def _make_collector(cryptocompare=True, newsapi=True):
    c = SentimentCollector(timeout_seconds=5.0)
    c._cryptocompare_key = "cc-key" if cryptocompare else ""
    c._newsapi_key = "na-key" if newsapi else ""
    return c


class _FakeHttp:
    """side_effect per httpx.AsyncClient.get: risponde/erra in base all'URL."""

    def __init__(self, mode="ok"):
        self.mode = mode
        self.calls = 0

    async def __call__(self, url, params=None, headers=None):
        self.calls += 1
        if self.mode == "ok":
            if "cryptocompare" in url:
                return _json_response(200, {"Data": [{"title": "Bitcoin bull surge to new high"}]})
            if "newsapi" in url:
                return _json_response(200, {"articles": [{"title": "BTC rally as adoption grows"}]})
            return _rss_response(RSS_TEXT)
        if self.mode == "cc_fail":
            if "cryptocompare" in url:
                raise RuntimeError("cryptocompare down")
            if "newsapi" in url:
                return _json_response(200, {"articles": [{"title": "BTC rally adoption grows"}]})
            return _rss_response(RSS_TEXT)
        if self.mode == "both_fail":
            if "cryptocompare" in url or "newsapi" in url:
                raise RuntimeError("upstream down")
            return _rss_response(RSS_TEXT)
        if self.mode == "all_fail":
            raise RuntimeError("network down")
        raise AssertionError(f"unexpected mode {self.mode}")


class TestSentimentFallbackPriority:
    @pytest.mark.asyncio
    async def test_priority_order_cryptocompare_first(self):
        c = _make_collector()
        fake = _FakeHttp("ok")
        with patch("httpx.AsyncClient.get", new=fake):
            result = await c.collect(SYMBOL)
        assert isinstance(result, SentimentData)
        assert result.source.startswith("cryptocompare")
        assert "newsapi" in result.source
        assert "rss" in result.source
        assert any("bull" in h.lower() for h in result.top_headlines)

    @pytest.mark.asyncio
    async def test_fallback_to_newsapi_when_cryptocompare_fails(self):
        c = _make_collector()
        fake = _FakeHttp("cc_fail")
        with patch("httpx.AsyncClient.get", new=fake):
            result = await c.collect(SYMBOL)
        assert isinstance(result, SentimentData)
        assert "cryptocompare" not in result.source
        assert "newsapi" in result.source
        assert "rss" in result.source
        assert any("rally" in h.lower() for h in result.top_headlines)

    @pytest.mark.asyncio
    async def test_fallback_to_rss_when_both_key_sources_fail(self):
        c = _make_collector()
        fake = _FakeHttp("both_fail")
        with patch("httpx.AsyncClient.get", new=fake):
            result = await c.collect(SYMBOL)
        assert isinstance(result, SentimentData)
        assert result.source == "rss"
        assert "cryptocompare" not in result.source
        assert "newsapi" not in result.source

    @pytest.mark.asyncio
    async def test_keyword_fallback_when_all_sources_fail(self):
        c = _make_collector()
        fake = _FakeHttp("all_fail")
        with patch("httpx.AsyncClient.get", new=fake):
            result = await c.collect(SYMBOL)
        assert isinstance(result, SentimentData)
        assert result.source == "fallback"
        assert result.score == 0.0
        assert result.news_count == 0

    @pytest.mark.asyncio
    async def test_zero_keys_uses_rss_only(self):
        c = _make_collector(cryptocompare=False, newsapi=False)
        fake = _FakeHttp("ok")
        with patch("httpx.AsyncClient.get", new=fake):
            result = await c.collect(SYMBOL)
        assert isinstance(result, SentimentData)
        assert result.source == "rss"
        assert fake.calls == 3  # solo i 3 feed RSS, nessuna chiamata keyed

    @pytest.mark.asyncio
    async def test_cache_prevents_repeated_calls_within_5min(self):
        c = _make_collector()
        fake = _FakeHttp("ok")
        with patch("httpx.AsyncClient.get", new=fake):
            await c.collect(SYMBOL)
            calls_after_first = fake.calls
            assert calls_after_first == 5  # CC + NewsAPI + 3 feed RSS
            await c.collect(SYMBOL)
            # nessuna nuova chiamata di rete: hit dalla cache 5 min
            assert fake.calls == calls_after_first


class TestSentimentCompactLogging:
    @pytest.mark.asyncio
    async def test_dns_failure_logs_compact_warning_not_full_traceback(self, caplog):
        import socket

        async def _dns_fail(url, params=None, headers=None):
            raise socket.gaierror("Name or service not known")

        c = _make_collector()
        with caplog.at_level(logging.WARNING, logger="app.scalping.intelligence.collectors.sentiment"):
            with patch("httpx.AsyncClient.get", new=_dns_fail):
                r1 = await c.collect(SYMBOL)
                warnings_after_first = sum(1 for r in caplog.records if r.levelno == logging.WARNING)
                r2 = await c.collect(SYMBOL)
                warnings_after_second = sum(1 for r in caplog.records if r.levelno == logging.WARNING)

        assert r1.source == "fallback"
        assert r2.source == "fallback"
        # secondo collect fallito: NON deve aggiungere warning (log compatto)
        assert warnings_after_second == warnings_after_first
        assert warnings_after_first > 0
        # mai traceback / ERROR
        assert not any(r.levelno >= logging.ERROR for r in caplog.records)
        assert not any(r.exc_info for r in caplog.records)
