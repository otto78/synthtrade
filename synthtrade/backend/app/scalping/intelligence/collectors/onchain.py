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

# Chain supportate nativamente da Blockchair
_CHAIN_MAP = {"btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin"}
# Usate come proxy macro per simboli non on-chain nativi (es. OKB-EUR)
_MACRO_PROXY_CHAINS = ["btc", "eth"]


class OnChainCollector:
    """Collettore dati on-chain da Dune e Blockchair.

    Per simboli non on-chain nativi (es. OKB-EUR) usa i dati BTC/ETH di
    Blockchair come proxy macro: la variazione di prezzo 24h di BTC/ETH e'
    un segnale direzionale di mercato applicabile anche ad asset spot EUR.
    """

    def __init__(self, timeout_seconds: float = 15.0):
        self._timeout = timeout_seconds
        self._dune_key = settings.scalping.DUNE_API_KEY
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("onchain")

    # Chain supportate da Blockchair
    _SUPPORTED_CHAINS = set(_CHAIN_MAP.keys())

    @staticmethod
    def _base_symbol(symbol: str) -> str:
        s = symbol.lower()
        for suffix in ("usdt", "usdc", "usd", "eur"):
            s = s.replace(suffix, "")
        return s.replace("-", "").replace("_", "")

    async def collect(self, symbol: str = "BTC") -> Optional[OnChainData]:
        if not self._cb.is_available():
            return None
        base_symbol = self._base_symbol(symbol)
        has_dune = bool(self._dune_key)
        is_native = base_symbol in self._SUPPORTED_CHAINS

        # Chain Blockchair da interrogare: il simbolo nativo se supportato,
        # altrimenti il proxy macro BTC+ETH.
        chains = [base_symbol] if is_native else list(_MACRO_PROXY_CHAINS)
        is_proxy = not is_native

        # Skip rapido: nessuna fonte disponibile
        if not has_dune and not chains:
            logger.debug("OnChainCollector: skip per %s (non supportato e Dune non configurato)", symbol)
            return None

        # 1. Tenta Dune Analytics (se abbiamo la query ID e la key)
        dune_data = await self._fetch_dune_data(base_symbol)

        # 2. Raccogli da Blockchair (transazioni, hashrate, momentum 24h)
        blockchair_data = await self._fetch_blockchair_stats(chains)

        if not dune_data and not blockchair_data:
            return None

        self._cb.on_success()
        if is_proxy:
            source = "blockchair_proxy:" + "+".join(chains)
        elif dune_data:
            source = "dune+blockchair"
        else:
            source = "blockchair"

        return OnChainData(
            symbol=symbol,
            exchange_net_flow=dune_data.get("net_flow"),
            active_addresses=blockchair_data.get("active_addresses"),
            transaction_count=blockchair_data.get("transaction_count"),
            hash_rate=blockchair_data.get("hash_rate"),
            price_change_24h_pct=blockchair_data.get("price_change_24h_pct"),
            proxy_symbol="+".join(chains) if is_proxy else None,
            source=source,
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

    async def _fetch_blockchair_stats(self, chains: list[str]) -> dict:
        """Fetch stats fondamentali da Blockchair per una o piu' chain.

        Per il proxy macro aggrega transazioni e hashrate e media la
        variazione di prezzo 24h tra le chain richieste.
        """
        if not chains:
            return {}

        try:
            per_chain: dict[str, dict] = {}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for ch in chains:
                    chain = _CHAIN_MAP.get(ch)
                    if not chain:
                        continue
                    try:
                        response = await client.get(BLOCKCHAIR_STATS_URL.format(chain))
                        if response.status_code == 200:
                            per_chain[ch] = response.json().get("data", {})
                    except Exception as e:
                        logger.warning("Blockchair on-chain error (%s): %s", ch, e)

            if not per_chain:
                return {}

            tx_sum = sum(int(r.get("transactions_24h", 0) or 0) for r in per_chain.values())
            changes = [
                float(r["market_price_usd_change_24h_percentage"])
                for r in per_chain.values()
                if r.get("market_price_usd_change_24h_percentage") is not None
            ]
            avg_change = sum(changes) / len(changes) if changes else None
            btc = per_chain.get("btc", {})
            hr = btc.get("hashrate_24h")

            return {
                # Blockchair non espone active_addresses_24h sulle stats globali
                "active_addresses": None,
                "transaction_count": tx_sum,
                "hash_rate": Decimal(str(hr)) if hr else None,
                "price_change_24h_pct": avg_change,
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

        Proxy macro (BTC/ETH): la variazione prezzo 24h e' un segnale
        direzionale di mercato applicabile anche ad asset spot EUR.
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

        # Momentum macro (proxy BTC/ETH): variazione prezzo 24h
        if data.price_change_24h_pct is not None:
            score += max(-30.0, min(30.0, float(data.price_change_24h_pct)))

        return max(-100.0, min(100.0, score))
