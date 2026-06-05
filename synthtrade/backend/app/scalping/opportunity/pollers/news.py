"""News Poller (TASK-810).

Aggregatore multi-fonte per news crypto.
"""

import asyncio
import logging
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional
import re

import httpx
from app.scalping.models.opportunity import PollerResult, OpportunitySource


logger = logging.getLogger(__name__)

# RSS feeds crypto (no API key required)
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss",  # 308 redirect if trailing slash present
    # Removed: https://www.theblock.co/rss returns 404 (RSS endpoint deprecated)
]


class NewsPoller:
    """Aggregatore di news da fonti multiple (RSS + API se disponibili)."""

    def __init__(self):
        self._last_hashes: set = set()
        self.source = OpportunitySource.CRYPTOPANIC

    async def fetch(self) -> List[PollerResult]:
        """Recupera news da tutte le fonti RSS."""
        results = []

        for feed_url in RSS_FEEDS:
            items = await self._fetch_rss_feed(feed_url)
            results.extend(items)

        return results

    async def _fetch_rss_feed(self, feed_url: str) -> List[PollerResult]:
        """Recupera un singolo feed RSS."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(feed_url)
                resp.raise_for_status()

            root = ET.fromstring(resp.text)
            items = root.findall(".//item")

            for item in items[:10]:  # Limit to latest 10 per feed
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")

                title = (title_elem.text or "") if title_elem is not None else ""
                link = (link_elem.text or "") if link_elem is not None else ""
                summary = ((desc_elem.text or "")[:500]) if desc_elem is not None else None

                # Generate hash for deduplication
                content_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                if content_hash in self._last_hashes:
                    continue

                self._last_hashes.add(content_hash)

                # Try to extract symbol
                symbol = self._extract_symbol(title + " " + (summary or ""))

                # Parse published date
                published_at = None
                pub_date_elem = item.find("pubDate")
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at = parsedate_to_datetime(pub_date_elem.text)
                    except Exception:
                        pass

                results.append(PollerResult(
                    source=self.source,
                    title=title,
                    description=summary,
                    url=link,
                    published_at=published_at,
                    symbol=symbol,
                    raw_data={"hash": content_hash, "feed": feed_url},
                ))

        except Exception as e:
            logger.error(f"NewsPoller RSS error ({feed_url}): {e}")

        return results

    def _extract_symbol(self, text: str) -> Optional[str]:
        """Estrae il simbolo dal testo news."""
        # Pattern: "$XYZ" or "XYZ token"
        match = re.search(r'\$([A-Z]{3,})', text)
        if match:
            return f"{match.group(1)}USDT"
        match = re.search(r'\b([A-Z]{3,})\s+(?:token|coin|price)\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}USDT"
        return None

    def get_default_interval(self) -> int:
        """Polling ogni 5 minuti."""
        return 300