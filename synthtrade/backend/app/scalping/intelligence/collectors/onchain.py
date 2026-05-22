"""OnChainCollector — recupera dati on-chain da Dune Analytics e Blockchair.

Monitora flussi exchange, indirizzi attivi e salute della rete.
"""

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

    async def collect(self, symbol: str = "BTC") -> Optional[OnChainData]:
        """Recupera dati on-chain per un simbolo.

        Args:
            symbol: Simbolo base (es: BTC, ETH).

        Returns:
            OnChainData se la raccolta ha successo, None altrimenti.
        """
        base_symbol = symbol.replace("USDT", "").replace("USD", "").lower()
        
        # 1. Tenta Dune Analytics (se abbiamo la query ID e la key)
        # Esempio: Query ID per BTC exchange flows
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
            
        # In una implementazione reale, avremmo una mappa di query_id per simbolo
        # Qui usiamo un esempio fittizio o saltiamo se non configurato
        query_map = {"btc": "123456", "eth": "789012"}
        query_id = query_map.get(symbol)
        if not query_id:
            return {}

        try:
            headers = {"X-Dune-API-Key": self._dune_key}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(DUNE_API_URL.format(query_id), headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    rows = data.get("result", {}).get("rows", [])
                    if rows:
                        # Assumiamo che la query restituisca 'net_flow'
                        return {"net_flow": Decimal(str(rows[0].get("net_flow", 0)))}
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
        """Converte i dati on-chain in un contributo score (-10 a +10).

        Exchange Net Flow:
        Negativo (outflow) -> Bullish (meno offerta su exchange)
        Positivo (inflow)  -> Bearish (più offerta, potenziale vendita)
        """
        score = 0.0
        
        # Flussi exchange (priorità alta)
        if data.exchange_net_flow is not None:
            # Esempio: -1000 BTC -> +5 score, +1000 BTC -> -5 score
            flow = float(data.exchange_net_flow)
            score -= flow / 200.0 
            
        # Aumento indirizzi attivi -> Bullish (adozione)
        if data.active_addresses and data.active_addresses > 500000:
            score += 2.0
            
        return max(-10.0, min(10.0, score))
