"""SentimentCollector — recupera sentiment da NewsAPI, CryptoCompare e RSS feeds.

Analizza titoli e frequenza news per determinare un bias di mercato.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
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


class SentimentCollector:
    """Collettore sentiment da NewsAPI e CryptoCompare."""

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds
        self._newsapi_key = settings.scalping.NEWSAPI_API_KEY
        self._cryptocompare_key = settings.scalping.CRYPTOCOMPARE_API_KEY

    async def collect(self, symbol: str = "BTC") -> Optional[SentimentData]:
        """Recupera e analizza il sentiment per un simbolo.

        Args:
            symbol: Simbolo base (es: BTC, ETH).

        Returns:
            SentimentData se la raccolta ha successo, None altrimenti.
        """
        # Rimuovi USDT se presente (es: BTCUSDT -> BTC)
        base_symbol = symbol.replace("USDT", "").replace("USD", "").upper()
        
        headlines = []
        news_count = 0
        
        # 1. Raccogli da CryptoCompare (solo se API key configurata)
        if self._cryptocompare_key:
            cc_news = await self._fetch_cryptocompare(base_symbol)
            for item in cc_news:
                headlines.append(item.get("title", ""))
                news_count += 1
        
        # 2. Raccogli da NewsAPI (se disponibile key)
        if self._newsapi_key and news_count < 10:
            api_news = await self._fetch_newsapi(base_symbol)
            for item in api_news:
                headlines.append(item.get("title", ""))
                news_count += 1
        
        # 3. Fallback gratuito: RSS feeds (sempre disponibili)
        if news_count < 5:
            rss_news = await self._fetch_rss_feeds()
            for item in rss_news:
                headlines.append(item.get("title", ""))
                news_count += 1

        if not headlines:
            return None

        # 4. Analisi semplificata del sentiment basata su keyword
        sentiment_score = self._analyze_sentiment(headlines)

        # Determina fonte
        sources = []
        if self._cryptocompare_key:
            sources.append("cryptocompare")
        if self._newsapi_key:
            sources.append("newsapi")
        sources.append("rss")
        
        return SentimentData(
            symbol=symbol,
            score=sentiment_score,
            news_count=news_count,
            top_headlines=headlines[:5],
            source="+".join(sources)
        )

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
            logger.warning("CryptoCompare fetch error: %s", e)
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
            logger.warning("NewsAPI fetch error: %s", e)
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
                logger.warning("RSS fetch error for %s: %s", feed_url, e)
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
