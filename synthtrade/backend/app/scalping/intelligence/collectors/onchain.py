"""OnChainCollector — recupera dati on-chain da Dune Analytics e Blockchair.

Monitora flussi exchange, indirizzi attivi e salute della rete.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from app.config import settings
from app.scalping.models.intelligence import OnChainData

logger = logging.getLogger(__name__)

DUNE_API_URL = "https://api.dune.com/api/v1/query/{}/results"
BLOCKCHAIR_STATS_URL = "https://api.blockchair.com/{}/stats"


class OnChainCollector:
    """Collettore dati on-chain da Dune e Blockchair."""

    def __init__(self, timeout_seconds: float = 15.0):
        self._timeout = timeout_seconds
        self._dune_key = settings.scalping.DUNE_API_KEY
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("onchain")

    # Chain supportate da Blockchair
    _SUPPORTED_CHAINS = {"btc", "eth", "ltc"}

    async def collect(self, symbol: str = "BTC") -> Optional[OnChainData]:
        if not self._cb.is_available():
            return None
        base_symbol = symbol.replace("USDT", "").replace("USDC", "").replace("USD", "").lower()

        # Skip rapido: se il simbolo non è supportato da Blockchair E Dune non è configurato,
        # non fare chiamate HTTP inutili.
        has_dune = bool(self._dune_key)
        has_blockchair = base_symbol in self._SUPPORTED_CHAINS
        if not has_dune and not has_blockchair:
            logger.debug("OnChainCollector: skip per %s (non supportato e Dune non configurato)", symbol)
            return None

        # 1. Tenta Dune Analytics (se abbiamo la query ID e la key)
        dune_data = await self._fetch_dune_data(base_symbol)

        # 2. Raccogli da Blockchair (active addresses, transactions)
        blockchair_data = await self._fetch_blockchair_stats(base_symbol)

        if not dune_data and not blockchair_data:
            return None

        return OnChainData(
            symbol=symbol,
            exchange_net_flow=dune_data.get("net_flow"),
            active_addresses=blockchair_data.get("active_addresses"),
            transaction_count=blockchair_data.get("transaction_count"),
            hash_rate=blockchair_data.get("hash_rate"),
            source="dune+blockchair" if dune_data else "blockchair",
            timestamp=datetime.now(timezone.utc)
        )

    async def _fetch_dune_data(self, symbol: str) -> dict:
        """Fetch dati da Dune Analytics."""
        if not self._dune_key:
            return {}
            
        # Mappa dinamica basata su settings
        query_map = {
            "btc": settings.scalping.DUNE_QUERY_ID_BTC,
            "eth": settings.scalping.DUNE_QUERY_ID_ETH
        }
        
        query_id = query_map.get(symbol)
        if not query_id or query_id == '0':
            return {}

        try:
            headers = {"X-Dune-API-Key": self._dune_key}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(DUNE_API_URL.format(query_id), headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    rows = data.get("result", {}).get("rows", [])
                    if rows:
                        row = rows[0]
                        net_flow = row.get("net_flow") or row.get("netflow") or row.get("value")
                        if net_flow is not None:
                            return {"net_flow": Decimal(str(net_flow))}
                elif response.status_code == 404:
                    logger.debug("Dune Query ID %s not found", query_id)
        except asyncio.CancelledError:
            logger.debug("Dune Analytics fetch cancelled (shutdown)")
            return {}
        except Exception as e:
            logger.warning("Dune Analytics fetch error: %s", e)
        return {}

    async def _fetch_blockchair_stats(self, symbol: str) -> dict:
        """Fetch stats fondamentali da Blockchair."""
        chain_map = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
        chain = chain_map.get(symbol)
        if not chain:
            return {}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(BLOCKCHAIR_STATS_URL.format(chain))
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    return {
                        "active_addresses": data.get("nodes"), # Esempio, nodes non è active addresses ma ok
                        "transaction_count": data.get("transactions_24h"),
                        "hash_rate": Decimal(str(data.get("hashrate_24h", 0))) if data.get("hashrate_24h") else None
                    }
        except Exception as e:
            logger.warning("Blockchair on-chain error: %s", e)
        return {}

    @staticmethod
    def onchain_to_score(data: OnChainData) -> float:
        """Converte i dati on-chain in un contributo score (-100 a +100).

        Exchange Net Flow:
        Negativo (outflow) -> Bullish (meno offerta su exchange)
        Positivo (inflow)  -> Bearish (più offerta, potenziale vendita)
        """
        score = 0.0
        
        # Flussi exchange (priorità alta)
        if data.exchange_net_flow is not None:
            # Esempio: -1000 BTC -> +50 score, +1000 BTC -> -50 score
            flow = float(data.exchange_net_flow)
            score -= flow / 20.0 
            
        # Aumento indirizzi attivi -> Bullish (adozione)
        if data.active_addresses and data.active_addresses > 500000:
            score += 20.0
            
        return max(-100.0, min(100.0, score))
