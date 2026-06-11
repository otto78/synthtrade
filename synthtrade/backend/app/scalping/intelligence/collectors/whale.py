"""WhaleCollector — monitora grandi movimenti on-chain.

Fonti per simbolo:
  BTC/LTC: Blockchair stats (gratuito, no key)
  ETH:     Etherscan API (gratuito, no key per query pubbliche)
  BNB:     BscScan API (gratuito, no key per query pubbliche)
  Altri:   CryptoCompare news fallback per keyword "whale"

RIMOSSO: RSSHub bridge (rsshub.app/telegram/channel/whale_alert) — inaffidabile.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from app.scalping.models.intelligence import WhaleData

logger = logging.getLogger(__name__)

# API pubbliche gratuite (no key)
BLOCKCHAIR_STATS_URL = "https://api.blockchair.com/{}/stats"
BSCSCAN_URL = "https://api.bscscan.com/api"
ETHERSCAN_URL = "https://api.etherscan.io/api"
CRYPTOCOMPARE_NEWS_URL = "https://min-api.cryptocompare.com/data/v2/news/"

# Soglia minima USD per considerare una transazione "whale"
WHALE_MIN_USD = 500_000


class WhaleCollector:
    """Collettore movimenti whale on-chain.

    Usa sorgenti gratuite e specifiche per ogni blockchain:
    - BNB → BscScan (BSC large txs)
    - ETH → Etherscan (large txs)
    - BTC/LTC → Blockchair (fee spikes + volume 24h)
    - Fallback → CryptoCompare news con keyword "whale"
    """

    def __init__(self, timeout_seconds: float = 12.0):
        self._timeout = timeout_seconds

    async def collect(self, symbol: str = "BTC") -> Optional[WhaleData]:
        """Rileva attività whale recente per un simbolo.

        Returns:
            WhaleData se trovati dati, None se nessuna sorgente ha risposto.
        """
        base_symbol = symbol.replace("USDT", "").replace("USDC", "").replace("USD", "").lower()

        whale_count = 0
        volume = Decimal("0")
        found_data = False

        if base_symbol == "bnb":
            result = await self._fetch_bscscan(base_symbol)
            whale_count += result.get("count", 0)
            volume += result.get("volume", Decimal("0"))
            found_data = True

        elif base_symbol == "eth":
            result = await self._fetch_etherscan(base_symbol)
            whale_count += result.get("count", 0)
            volume += result.get("volume", Decimal("0"))
            found_data = True

        elif base_symbol in ("btc", "ltc"):
            result = await self._fetch_blockchair_stats(base_symbol)
            whale_count += result.get("whale_count", 0)
            volume += result.get("volume", Decimal("0"))
            found_data = True

        # Per tutti: news fallback se nessun dato strutturato
        if not found_data or whale_count == 0:
            news_result = await self._fetch_whale_news_fallback(base_symbol)
            if news_result.get("count", 0) > 0:
                whale_count += news_result["count"]
                found_data = True

        if not found_data:
            return None

        return WhaleData(
            symbol=symbol,
            whale_transaction_count=whale_count,
            large_transfer_volume=volume,
            recent_whale_activity=whale_count >= 1,
            timestamp=datetime.now(timezone.utc)
        )

    async def _fetch_bscscan(self, symbol: str) -> dict:
        """Fetch whale data da BscScan (BSC) — gratuito, no key.

        Conta le transazioni BNB > 500k USD nelle ultime ore
        usando la lista delle transazioni per valore elevato.
        """
        try:
            # BscScan: statistiche rete BSC
            params = {
                "module": "stats",
                "action": "bnbsupply",
            }
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(BSCSCAN_URL, params=params)
                if response.status_code == 200:
                    data = response.json()
                    # Usiamo il fatto che BscScan è up come proxy per attività BNB
                    # e contiamo le whale txs cercando grandi transfer pubblici
                    # via la API token txlist per WBNB con valore alto
                    params2 = {
                        "module": "account",
                        "action": "tokentx",
                        "contractaddress": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
                        "page": 1,
                        "offset": 20,
                        "sort": "desc",
                        "startblock": 0,
                        "endblock": 999999999,
                    }
                    resp2 = await client.get(BSCSCAN_URL, params=params2)
                    if resp2.status_code == 200:
                        txs = resp2.json().get("result", [])
                        if isinstance(txs, list):
                            whale_count = 0
                            whale_volume = Decimal("0")
                            for tx in txs:
                                # tokenDecimal 18 per WBNB
                                try:
                                    value_raw = int(tx.get("value", "0"))
                                    value_bnb = value_raw / 1e18
                                    # BNB ~$600: 833 BNB ≈ $500k
                                    if value_bnb > 833:
                                        whale_count += 1
                                        whale_volume += Decimal(str(value_bnb))
                                except (ValueError, TypeError):
                                    pass
                            logger.debug("BscScan whale: count=%d volume=%.2f BNB", whale_count, float(whale_volume))
                            return {"count": whale_count, "volume": whale_volume}
        except Exception as e:
            logger.debug("BscScan fetch error: %s", e)
        return {"count": 0, "volume": Decimal("0")}

    async def _fetch_etherscan(self, symbol: str) -> dict:
        """Fetch whale data da Etherscan — gratuito, no key per chiamate base."""
        try:
            # Lista ultime grandi transazioni ETH (nessun filtro valore disponibile gratis,
            # ma possiamo usare beaconscan o solo news fallback)
            params = {
                "module": "stats",
                "action": "ethsupply",
            }
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(ETHERSCAN_URL, params=params)
                if response.status_code == 200:
                    # Senza key Etherscan non permette query filtrate per valore
                    # Ritorniamo 0 contando sul news fallback
                    pass
        except Exception as e:
            logger.debug("Etherscan fetch error: %s", e)
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
                            if "whale" in title or "large transaction" in title or "large transfer" in title:
                                count += 1
                        if count > 0:
                            logger.debug("Whale news fallback for %s: count=%d", symbol, count)
                        return {"count": count, "volume": Decimal("0")}
        except Exception as e:
            logger.debug("Whale news fallback error: %s", e)
        return {"count": 0, "volume": Decimal("0")}

    async def _fetch_blockchair_stats(self, symbol: str) -> dict:
        """Fetch stats da Blockchair (solo BTC/ETH/LTC)."""
        chain_map = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
        chain = chain_map.get(symbol)
        if not chain:
            return {"whale_count": 0, "volume": Decimal("0")}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(BLOCKCHAIR_STATS_URL.format(chain))
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    return {
                        "whale_count": 1 if data.get("suggested_transaction_fee_per_byte_sat", 0) > 150 else 0,
                        "volume": Decimal(str(data.get("volume_24h", 0))) / 10**8
                    }
        except Exception as e:
            logger.warning("Blockchair stats error: %s", e)
        return {"whale_count": 0, "volume": Decimal("0")}

    @staticmethod
    def whale_to_score(data: WhaleData) -> float:
        """Converte l'attività whale in un contributo score (0 a +10).

        Usa whale_transaction_count come indicatore primario.
        """
        if data.whale_transaction_count > 0:
            score = min(10.0, data.whale_transaction_count * 2.5)
            return score

        # Fallback: usa large_transfer_volume se significativo (> 10 BNB/ETH/BTC)
        vol = float(data.large_transfer_volume)
        if vol > 10.0:
            import math
            score = min(10.0, math.log10(max(vol, 1.0)) * 2.0)
            return round(score, 1)

        return 0.0
