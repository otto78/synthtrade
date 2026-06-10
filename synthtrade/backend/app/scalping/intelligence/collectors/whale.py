"""WhaleCollector — monitora grandi movimenti on-chain (Whale Alert RSS, Blockchair).

Rileva grandi trasferimenti che possono indicare pressure buy/sell imminente.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
import xml.etree.ElementTree as ET

import httpx
from app.scalping.models.intelligence import WhaleData

logger = logging.getLogger(__name__)

# RSSHub bridge per il canale Telegram di Whale Alert (Opzione Free)
WHALE_ALERT_RSS_URL = "https://rsshub.app/telegram/channel/whale_alert"
BLOCKCHAIR_STATS_URL = "https://api.blockchair.com/{}/stats"
# Fallback news/alerts da CryptoCompare
CRYPTOCOMPARE_NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/"


class WhaleCollector:
    """Collettore movimenti whale on-chain."""

    def __init__(self, timeout_seconds: float = 12.0):
        self._timeout = timeout_seconds

    async def collect(self, symbol: str = "BTC") -> Optional[WhaleData]:
        """Rileva attività whale recente per un simbolo.

        Args:
            symbol: Simbolo base (es: BTC, ETH).

        Returns:
            WhaleData se la raccolta ha successo, None altrimenti.
        """
        base_symbol = symbol.replace("USDT", "").replace("USD", "").lower()
        
        # 1. Raccogli da Whale Alert via RSSHub bridge
        rss_activity = await self._fetch_whale_alert_rss(base_symbol)
        
        # 2. Raccogli stats da Blockchair
        blockchair_activity = await self._fetch_blockchair_stats(base_symbol)
        
        # 3. Fallback: Cerca whale alert nei feed news se RSSHub è lento/down
        if rss_activity.get("count", 0) == 0:
            news_activity = await self._fetch_whale_news_fallback(base_symbol)
            rss_activity["count"] += news_activity.get("count", 0)
            rss_activity["volume"] += news_activity.get("volume", Decimal("0"))

        whale_count = rss_activity.get("count", 0) + blockchair_activity.get("whale_count", 0)
        volume = rss_activity.get("volume", Decimal("0")) + blockchair_activity.get("volume", Decimal("0"))

        return WhaleData(
            symbol=symbol,
            whale_transaction_count=whale_count,
            large_transfer_volume=volume,
            recent_whale_activity=whale_count >= 1,
            timestamp=datetime.now(timezone.utc)
        )

    async def _fetch_whale_alert_rss(self, symbol: str) -> dict:
        """Fetch e parse Whale Alert via RSSHub bridge."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                # Usiamo uno user-agent per evitare blocchi base
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SynthTrade/1.0"}
                response = await client.get(WHALE_ALERT_RSS_URL, headers=headers)
                
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    count = 0
                    volume = Decimal("0")
                    
                    for item in root.findall(".//item"):
                        title_elem = item.find("title")
                        desc_elem = item.find("description")
                        
                        text = ""
                        if title_elem is not None and title_elem.text is not None: text += title_elem.text.lower()
                        if desc_elem is not None and desc_elem.text is not None: text += desc_elem.text.lower()
                        
                        if symbol in text:
                            count += 1
                            # Tentativo di estrazione volume (es: "1,000 #BTC")
                            try:
                                words = text.split()
                                for i, word in enumerate(words):
                                    if symbol in word or f"#{symbol}" in word:
                                        vol_str = words[i-1].replace(",", "")
                                        volume += Decimal(vol_str)
                                        break
                            except:
                                pass
                    return {"count": count, "volume": volume}
        except Exception as e:
            logger.debug("Whale Alert RSS bridge error: %s", e)
        return {"count": 0, "volume": Decimal("0")}

    async def _fetch_whale_news_fallback(self, symbol: str) -> dict:
        """Fallback: cerca keyword 'whale' nelle news di CryptoCompare."""
        try:
            params = {"categories": symbol, "excludeCategories": "Sponsored"}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(CRYPTOCOMPARE_NEWS_URL, params=params)
                if response.status_code == 200:
                    news_data = response.json().get("Data")
                    if isinstance(news_data, list):
                        count = 0
                        for news in news_data:
                            title = news.get("title", "").lower()
                            if "whale" in title or "large transaction" in title:
                                count += 1
                    return {"count": count, "volume": Decimal("0")}
        except:
            pass
        return {"count": 0, "volume": Decimal("0")}

    async def _fetch_blockchair_stats(self, symbol: str) -> dict:
        """Fetch stats da Blockchair."""
        chain_map = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
        chain = chain_map.get(symbol)
        if not chain:
            return {"whale_count": 0, "volume": Decimal("0")}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(BLOCKCHAIR_STATS_URL.format(chain))
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    # Se il volume 24h è alto rispetto alla media o ci sono picchi
                    return {
                        "whale_count": 1 if data.get("suggested_transaction_fee_per_byte_sat", 0) > 150 else 0,
                        "volume": Decimal(str(data.get("volume_24h", 0))) / 10**8
                    }
        except Exception as e:
            logger.warning("Blockchair stats error: %s", e)
        return {"whale_count": 0, "volume": Decimal("0")}

    @staticmethod
    def whale_to_score(data: WhaleData) -> float:
        """Converte l'attività whale in un contributo score (-10 a +10).
        
        Usa whale_transaction_count come indicatore primario.
        Se count è 0 ma large_transfer_volume è significativo (> 10 BTC),
        calcola lo score dal volume come fallback.
        """
        if data.whale_transaction_count > 0:
            score = min(10.0, data.whale_transaction_count * 2.5)
            return score
        
        # Fallback: usa large_transfer_volume se significativo
        vol = float(data.large_transfer_volume)
        if vol > 10.0:
            # Scala logaritmica: 10 BTC → 1, 100 BTC → 3, 1000 BTC → 5, 1M BTC → 10
            import math
            score = min(10.0, math.log10(max(vol, 1.0)) * 2.0)
            return round(score, 1)
        
        return 0.0
