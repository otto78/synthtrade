"""Binance RSS Poller (TASK-810).

Polla il feed RSS ufficiale Binance per announcements.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from xml.etree import ElementTree

import httpx

from app.scalping.models.opportunity import PollerResult, OpportunitySource


logger = logging.getLogger(__name__)

BINANCE_RSS_URL = "https://www.binance.com/en/support/announcement/rss"


class BinanceRSSPoller:
    """Polla il feed RSS Binance per rilevare nuove listing e launchpool."""

    def __init__(self, rss_url: str = BINANCE_RSS_URL):
        self.source = OpportunitySource.BINANCE_RSS
        self.rss_url = rss_url
        self._last_hashes: set = set()

    async def fetch(self) -> List[PollerResult]:
        """Recupera announcements dal feed RSS."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.rss_url)
                resp.raise_for_status()

            root = ElementTree.fromstring(resp.text)
            items = root.findall(".//item")

            for item in items[:20]:  # Limit to latest 20
                title = item.findtext("title", default="")
                link = item.findtext("link", default="")
                description = item.findtext("description", default="")
                pub_date = item.findtext("pubDate")

                # Parse published date
                published_at = None
                if pub_date:
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at = parsedate_to_datetime(pub_date)
                    except Exception:
                        pass

                # Generate hash for deduplication
                content_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                if content_hash in self._last_hashes:
                    continue

                self._last_hashes.add(content_hash)

                # Extract symbol from title if present (e.g., "Adds trading pairs for XYZ/USDT")
                symbol = self._extract_symbol(title)

                results.append(PollerResult(
                    source=self.source,
                    title=title,
                    description=description[:500] if description else None,
                    url=link,
                    published_at=published_at,
                    symbol=symbol,
                    raw_data={"hash": content_hash},
                ))

        except Exception as e:
            logger.error(f"BinanceRSSPoller fetch error: {e}")

        return results

    def _extract_symbol(self, title: str) -> Optional[str]:
        """Estrae il simbolo trading da un titolo announcement."""
        import re
        # Pattern: "Adds trading pairs for XYZ/USDT" or "Lists XYZ/USDT"
        match = re.search(r'(?:trading pairs? for|Lists?)\s+([A-Z]+/USDT)', title)
        if match:
            return match.group(1).replace("/", "USDT").replace("USDTUSDT", "USDT")
        # Also check for "XYZ/USDT" patterns
        match = re.search(r'([A-Z]{3,})/USDT', title)
        if match:
            return f"{match.group(1)}USDT"
        return None

    def get_default_interval(self) -> int:
        """Polling ogni 5 minuti."""
        return 300