"""SentimentCollector — recupera sentiment da NewsAPI, CryptoCompare e RSS feeds.

Analizza titoli e frequenza news per determinare un bias di mercato.

Fallback robusto (TASK-1154): ordine di priorita' esplicito
  CryptoCompare (key opz.) -> NewsAPI (key opz.) -> RSS (free) -> fallback neutrale.
- Cache 5 min per evitare rate-limit (NewsAPI/CryptoCompare sono molto restrittivi).
- Log compatto: un solo warning per tipologia di errore consecutivo (es. DNS),
  nessuno stack trace ripetuto ogni minuto.
- Se TUTTE le sorgenti falliscono, ritorna un oggetto sentiment neutro (source="fallback")
  invece di None, cosi' il collector non appare come "no response" a ogni hiccup di rete.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

import httpx
from app.config import settings
from app.scalping.models.intelligence import SentimentData

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
CRYPTOCOMPARE_NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/"
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss",
    "https://cointelegraph.com/rss",
    "https://cryptonews.com/feed/",
]

CACHE_TTL_SEC = 300            # 5 minuti (TASK-1154: evita rate-limit)
NEWS_TARGET = 10              # numero massimo di headline utili
RSS_FALLBACK_THRESHOLD = 5    # sotto cui si attiva il fallback RSS


class SentimentCollector:
    """Collettore sentiment con fallback multi-sorgente robusto (TASK-1154)."""

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds
        self._newsapi_key = settings.scalping.NEWSAPI_API_KEY
        self._cryptocompare_key = settings.scalping.CRYPTOCOMPARE_API_KEY
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("sentiment")
        self._cache: Dict[str, Tuple[float, SentimentData]] = {}
        self._last_error_signature: Optional[str] = None  # per log compatto

    async def collect(self, symbol: str = "BTC") -> Optional[SentimentData]:
        if not self._cb.is_available():
            return None

        cache_key = self._cache_key(symbol)
        cached = self._cache.get(cache_key)
        if cached is not None:
            ts, data = cached
            if time.monotonic() - ts < CACHE_TTL_SEC:
                self._cb.on_success()
                return data

        # Rimuovi USDT se presente (es: BTCUSDT -> BTC)
        base_symbol = symbol.replace("USDT", "").replace("USD", "").upper()

        headlines: List[str] = []
        sources: List[str] = []

        # 1. CryptoCompare (con key) — priorita' massima
        if self._cryptocompare_key:
            cc_news = await self._fetch_cryptocompare(base_symbol)
            if cc_news:
                headlines.extend(item.get("title", "") for item in cc_news)
                sources.append("cryptocompare")

        # 2. NewsAPI (con key) — se servono ancora headline
        if self._newsapi_key and len(headlines) < NEWS_TARGET:
            api_news = await self._fetch_newsapi(base_symbol)
            if api_news:
                headlines.extend(item.get("title", "") for item in api_news)
                sources.append("newsapi")

        # 3. RSS (free, sempre disponibile) — fallback se pochi dati
        if len(headlines) < RSS_FALLBACK_THRESHOLD:
            rss_news = await self._fetch_rss_feeds()
            if rss_news:
                headlines.extend(item.get("title", "") for item in rss_news)
                sources.append("rss")

        # Filtra eventuali titoli vuoti
        headlines = [h for h in headlines if h]

        if not headlines:
            # Tutte le sorgenti hanno fallito: fallback neutro (TASK-1154).
            # Ritorna un oggetto neutro invece di None per non segnare il
            # collector come "no response" ad ogni hiccup di rete.
            self._reset_error_signature()
            fallback = SentimentData(
                symbol=symbol,
                score=0.0,
                news_count=0,
                top_headlines=[],
                source="fallback",
            )
            self._cache[cache_key] = (time.monotonic(), fallback)
            self._cb.on_success()
            logger.debug("[sentiment] tutte le sorgenti fallite per %s -> fallback neutro", symbol)
            return fallback

        result = SentimentData(
            symbol=symbol,
            score=self._analyze_sentiment(headlines),
            news_count=len(headlines),
            top_headlines=headlines[:5],
            source="+".join(sources) if sources else "rss",
        )
        self._cache[cache_key] = (time.monotonic(), result)
        self._cb.on_success()
        self._reset_error_signature()
        return result

    def _cache_key(self, symbol: str) -> str:
        return symbol.replace("USDT", "").replace("USD", "").upper()

    def _log_compact(self, name: str, exc: Exception) -> None:
        """Logga un warning una sola volta per tipologia di errore consecutivo.

        Evita lo spam di stack trace DNS ripetuti (vedi recap 29-30/06 FearGreed).
        """
        sig = f"{name}:{type(exc).__name__}"
        if sig == self._last_error_signature:
            return
        self._last_error_signature = sig
        logger.warning("[sentiment] %s fetch fallito (%s): %s", name, type(exc).__name__, exc)

    def _reset_error_signature(self) -> None:
        self._last_error_signature = None

    async def _fetch_cryptocompare(self, symbol: str) -> List[dict]:
        """Fetch news da CryptoCompare."""
        try:
            params = {"categories": symbol, "excludeCategories": "Sponsored"}
            headers = {}
            if self._cryptocompare_key:
                headers["authorization"] = f"Apikey {self._cryptocompare_key}"

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(CRYPTOCOMPARE_NEWS_URL, params=params, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    news_data = data.get("Data")
                    if isinstance(news_data, list):
                        return news_data[:10]
                    return []
        except Exception as e:
            self._log_compact("cryptocompare", e)
        return []

    async def _fetch_newsapi(self, symbol: str) -> List[dict]:
        """Fetch news da NewsAPI."""
        try:
            params = {
                "q": symbol,
                "language": "en",
                "sortBy": "publishedAt",
                "apiKey": self._newsapi_key,
                "pageSize": 10
            }
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(NEWSAPI_URL, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("articles", [])
        except Exception as e:
            self._log_compact("newsapi", e)
        return []

    async def _fetch_rss_feeds(self) -> List[dict]:
        """Fetch news da RSS feeds gratuiti (sempre disponibili)."""
        all_headlines = []
        for feed_url in RSS_FEEDS:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(feed_url)
                    if response.status_code == 200:
                        root = ET.fromstring(response.text)
                        items = root.findall(".//item")
                        for item in items[:5]:
                            title_elem = item.find("title")
                            if title_elem is not None and title_elem.text:
                                all_headlines.append({"title": title_elem.text})
            except Exception as e:
                self._log_compact(f"rss:{feed_url}", e)
        return all_headlines[:10]

    def _analyze_sentiment(self, headlines: List[str]) -> float:
        """Analisi euristica del sentiment basata su keyword."""
        bullish_words = {"bull", "surge", "gain", "breakout", "rally", "growth", "positive", "high", "ath", "adoption", "buy", "support"}
        bearish_words = {"bear", "crash", "plummet", "drop", "sell", "negative", "low", "dump", "ban", "regulation", "scam", "hack", "resistance"}

        total_score = 0.0
        for title in headlines:
            words = set(title.lower().split())
            bull_matches = len(words.intersection(bullish_words))
            bear_matches = len(words.intersection(bearish_words))

            if bull_matches > bear_matches:
                total_score += 0.2
            elif bear_matches > bull_matches:
                total_score -= 0.2

        # Normalizza tra -1 e 1
        if not headlines:
            return 0.0

        avg_score = total_score / len(headlines)
        return max(-1.0, min(1.0, avg_score * 5))  # Amplifica un po' il segnale

    @staticmethod
    def sentiment_to_score(sentiment: float) -> float:
        """Converte il sentiment score in un contributo per SignalScore (-100 a +100)."""
        # Mappa -1 -> -100, 0 -> 0, 1 -> +100
        return max(-100.0, min(100.0, sentiment * 100.0))
