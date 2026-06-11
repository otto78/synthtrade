"""Binance Announcements Poller.

Polla gli annunci ufficiali Binance tramite API REST pubblica.
Sostituisce il feed RSS rimosso da Binance (body vuoto dal 2024).

API:
  https://www.binance.com/bapi/composite/v1/public/cms/article/list/query
  Parametri: pageNo, pageSize, type (1=New Listings, 2=Latest Activities, ecc.)
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.scalping.models.opportunity import PollerResult, OpportunitySource


logger = logging.getLogger(__name__)

BINANCE_ANNOUNCEMENTS_URL = (
    "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
)
BINANCE_ARTICLE_BASE = "https://www.binance.com/en/support/announcement/"


class BinanceRSSPoller:
    """Polla gli annunci Binance per rilevare nuove listing e launchpool.

    Usa la API REST pubblica (nessuna key richiesta) invece del feed RSS
    rimosso da Binance (risponde 200 ma body vuoto).
    """

    def __init__(self, rss_url: str = BINANCE_ANNOUNCEMENTS_URL):
        self.source = OpportunitySource.BINANCE_RSS
        self._last_hashes: set = set()
        # Teniamo traccia se l'API è mai risultata funzionante
        self._api_ok = True
        _logged_ok = False

    async def fetch(self) -> List[PollerResult]:
        """Recupera gli ultimi annunci Binance."""
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # type=1 = New Listings, type=2 = Latest Activities
                # Prendiamo entrambi i tipi più rilevanti per il trading
                for article_type in [1, 2]:
                    params = {
                        "pageNo": 1,
                        "pageSize": 10,
                        "type": article_type,
                    }
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SynthTrade/1.0",
                    }
                    resp = await client.get(
                        BINANCE_ANNOUNCEMENTS_URL, params=params, headers=headers
                    )

                    if resp.status_code != 200:
                        logger.debug("BinanceAnnouncements type=%d: HTTP %d", article_type, resp.status_code)
                        continue

                    data = resp.json()
                    articles = (
                        data.get("data", {}).get("catalogs", [{}])[0].get("articles", [])
                        if data.get("data", {}).get("catalogs")
                        else data.get("data", {}).get("articles", [])
                    )

                    if not articles:
                        # Prova struttura alternativa
                        articles = data.get("data", {}).get("list", [])

                    for article in articles:
                        title = article.get("title", "")
                        code = article.get("code", "")
                        release_date = article.get("releaseDate", 0)

                        if not title:
                            continue

                        url = f"{BINANCE_ARTICLE_BASE}{code}" if code else ""
                        content_hash = hashlib.md5(f"{title}{code}".encode()).hexdigest()

                        if content_hash in self._last_hashes:
                            continue

                        self._last_hashes.add(content_hash)

                        published_at = (
                            datetime.fromtimestamp(release_date / 1000, tz=timezone.utc)
                            if release_date
                            else None
                        )

                        symbol = self._extract_symbol(title)

                        results.append(
                            PollerResult(
                                source=self.source,
                                title=title,
                                description=f"Binance Announcement (type={article_type})",
                                url=url,
                                published_at=published_at,
                                symbol=symbol,
                                raw_data={"hash": content_hash, "code": code},
                            )
                        )

        except Exception as e:
            logger.debug("BinanceAnnouncementsPoller fetch error: %s", e)

        return results

    def _extract_symbol(self, title: str) -> Optional[str]:
        """Estrae il simbolo trading da un titolo announcement."""
        import re
        # "Will List XYZ" / "Lists XYZ/USDT" / "Adds trading pairs for XYZ/USDT"
        match = re.search(r'(?:Will List|Lists?|trading pairs? for)\s+([A-Z]{2,10})', title)
        if match:
            sym = match.group(1)
            if sym not in ("THE", "AND", "FOR", "NEW", "WITH"):
                return f"{sym}USDT"
        match = re.search(r'\b([A-Z]{3,8})/USDT\b', title)
        if match:
            return f"{match.group(1)}USDT"
        return None

    def get_default_interval(self) -> int:
        """Polling ogni 5 minuti."""
        return 300