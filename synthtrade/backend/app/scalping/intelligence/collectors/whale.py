"""WhaleCollector — monitora grandi movimenti on-chain (Whale Alert RSS, Blockchair).

Rileva grandi trasferimenti che possono indicare pressure buy/sell imminente.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import xml.etree.ElementTree as ET

import httpx
from app.scalping.models.intelligence import WhaleData

logger = logging.getLogger(__name__)

WHALE_ALERT_RSS_URL = "https://whale-alert.io/rss"
BLOCKCHAIR_STATS_URL = "https://api.blockchair.com/{}/stats"


class WhaleCollector:
    """Collettore movimenti whale on-chain."""

    def __init__(self, timeout_seconds: float = 10.0):
        self._timeout = timeout_seconds

    async def collect(self, symbol: str = "BTC") -> Optional[WhaleData]:
        """Rileva attività whale recente per un simbolo.

        Args:
            symbol: Simbolo base (es: BTC, ETH).

        Returns:
            WhaleData se la raccolta ha successo, None altrimenti.
        """
        base_symbol = symbol.replace("USDT", "").replace("USD", "").lower()
        
        # 1. Raccogli da Whale Alert RSS (generico, cross-chain)
        rss_activity = await self._fetch_whale_alert_rss(base_symbol)
        
        # 2. Raccogli stats da Blockchair (specifico per chain)
        blockchair_activity = await self._fetch_blockchair_stats(base_symbol)
        
        whale_count = rss_activity.get("count", 0) + blockchair_activity.get("whale_count", 0)
        volume = rss_activity.get("volume", Decimal("0")) + blockchair_activity.get("volume", Decimal("0"))

        if whale_count == 0 and volume == 0:
            # Ritorna comunque un oggetto vuoto per indicare "nessuna attività rilevata"
            return WhaleData(
                symbol=symbol,
                whale_transaction_count=0,
                large_transfer_volume=Decimal("0"),
                recent_whale_activity=False,
                timestamp=datetime.now(timezone.utc)
            )

        return WhaleData(
            symbol=symbol,
            whale_transaction_count=whale_count,
            large_transfer_volume=volume,
            recent_whale_activity=whale_count > 2,
            timestamp=datetime.now(timezone.utc)
        )

    async def _fetch_whale_alert_rss(self, symbol: str) -> dict:
        """Fetch e parse Whale Alert RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(WHALE_ALERT_RSS_URL)
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    count = 0
                    volume = Decimal("0")
                    
                    # Cerca il simbolo nel titolo/descrizione degli item
                    for item in root.findall(".//item"):
                        title = item.find("title").text.lower()
                        if symbol in title:
                            count += 1
                            # Esempio titolo: "1,000 #BTC (60,000,000 USD) transferred from Unknown to Binance"
                            # Parsing molto semplificato
                            try:
                                words = title.split()
                                vol_str = words[0].replace(",", "")
                                volume += Decimal(vol_str)
                            except:
                                pass
                    return {"count": count, "volume": volume}
        except Exception as e:
            logger.warning("Whale Alert RSS error: %s", e)
        return {"count": 0, "volume": Decimal("0")}

    async def _fetch_blockchair_stats(self, symbol: str) -> dict:
        """Fetch stats da Blockchair (active addresses, large transactions)."""
        # Blockchair usa nomi chain diversi
        chain_map = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
        chain = chain_map.get(symbol)
        if not chain:
            return {"whale_count": 0, "volume": Decimal("0")}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(BLOCKCHAIR_STATS_URL.format(chain))
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    # Blockchair non dà "whale count" diretto ma possiamo usare suggerimenti
                    # o semplicemente riportare se il volume mediano è alto
                    return {
                        "whale_count": 1 if data.get("suggested_transaction_fee_per_byte_sat", 0) > 100 else 0,
                        "volume": Decimal(str(data.get("volume_24h", 0))) / 10**8 # Esempio
                    }
        except Exception as e:
            logger.warning("Blockchair stats error: %s", e)
        return {"whale_count": 0, "volume": Decimal("0")}

    @staticmethod
    def whale_to_score(data: WhaleData) -> float:
        """Converte l'attività whale in un contributo score (-10 a +10).

        Nota: Whale activity è ambigua (buy vs sell).
        Spesso inflow exchange = bearish, outflow = bullish.
        Qui usiamo una logica neutra/volatilità.
        """
        if not data.recent_whale_activity:
            return 0.0
        
        # Se c'è molta attività, aumentiamo lo score di "allerta" (può essere positivo o negativo)
        # Per ora ritorniamo un valore piccolo che indica volatilità in arrivo.
        return min(10.0, data.whale_transaction_count * 2.0)
