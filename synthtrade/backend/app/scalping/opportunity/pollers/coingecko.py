"""CoinGecko Poller (TASK-810).

Polla Trending coins e News da CoinGecko.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from app.scalping.models.opportunity import PollerResult, OpportunitySource


logger = logging.getLogger(__name__)

TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"
NEWS_URL = "https://api.coingecko.com/api/v3/news"


class CoinGeckoPoller:
    """Polla trending coins e news da CoinGecko."""

    def __init__(self):
        self.source = OpportunitySource.COINGECKO_TRENDING
        self._last_hashes: set = set()

    async def fetch_trending(self) -> List[PollerResult]:
        """Recupera trending coins."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(TRENDING_URL)
                resp.raise_for_status()
            data = resp.json()

            for coin in data.get("coins", []):
                item = coin.get("item", {})
                symbol = item.get("symbol", "").upper()
                name = item.get("name", "")

                # Generate opportunity for high trending score
                title = f"{name} ({symbol}) trending on CoinGecko"
                content_hash = hashlib.md5(title.encode()).hexdigest()

                if content_hash in self._last_hashes:
                    continue

                self._last_hashes.add(content_hash)

                results.append(PollerResult(
                    source=self.source,
                    title=title,
                    description=f"Coin is trending, score: {item.get('score', 'N/A')}",
                    url=f"https://www.coingecko.com/en/coins/{item.get('id', '')}",
                    symbol=f"{symbol}USDT" if symbol else None,
                    raw_data={"hash": content_hash, "trending_score": item.get("score")},
                ))

        except Exception as e:
            logger.error(f"CoinGeckoPoller trending error: {e}")

        return results

    async def fetch_news(self) -> List[PollerResult]:
        """Recupera news da CoinGecko."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(NEWS_URL)
                resp.raise_for_status()
            data = resp.json()

            for article in data[:10]:  # Limit to latest 10
                title = article.get("title", "")
                link = article.get("url", "")

                content_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                if content_hash in self._last_hashes:
                    continue

                self._last_hashes.add(content_hash)

                # Try to extract symbol from title
                symbol = self._extract_symbol(title)

                results.append(PollerResult(
                    source=OpportunitySource.COINGECKO_NEWS,
                    title=title,
                    description=article.get("description", "")[:500] if article.get("description") else None,
                    url=link,
                    published_at=datetime.fromtimestamp(article.get("created_at", 0), tz=timezone.utc) if article.get("created_at") else None,
                    symbol=symbol,
                    raw_data={"hash": content_hash},
                ))

        except Exception as e:
            logger.error(f"CoinGeckoPoller news error: {e}")

        return results

    def _extract_symbol(self, title: str) -> Optional[str]:
        """Estrae il simbolo trading dal titolo news."""
        import re
        # Pattern: "$XYZ" or "XYZ token" or "(XYZ)"
        match = re.search(r'\$([A-Z]{3,})', title)
        if match:
            return f"{match.group(1)}USDT"
        match = re.search(r'\(([A-Z]{3,})\)', title)
        if match:
            return f"{match.group(1)}USDT"
        return None

    async def fetch(self) -> List[PollerResult]:
        """Esegue entrambi i fetch (trending + news)."""
        results = []
        results.extend(await self.fetch_trending())
        results.extend(await self.fetch_news())
        return results

    def get_default_interval(self) -> int:
        """Polling ogni 5 minuti."""
        return 300