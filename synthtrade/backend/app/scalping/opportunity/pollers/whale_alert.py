"""Whale Alert Poller (TASK-810).

Polla grandi transazioni on-chain.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
import os

import httpx
from app.scalping.models.opportunity import PollerResult, OpportunitySource


logger = logging.getLogger(__name__)

WHALE_ALERT_URL = "https://api.whale-alert.io/v1/transactions"


class WhaleAlertPoller:
    """Polla whale alert API per grandi movimenti di cripto."""

    def __init__(self, api_key: Optional[str] = None, min_value_usd: float = 100000):
        self.source = OpportunitySource.WHALE_ALERT
        self.api_key = api_key or os.getenv("WHALE_ALERT_API_KEY", "")
        self.min_value_usd = min_value_usd
        self._last_hashes: set = set()

    async def fetch(self) -> List[PollerResult]:
        """Recupera whale transactions."""
        results = []

        if not self.api_key:
            logger.warning("WhaleAlert API key not configured, skipping")
            return results

        try:
            params = {
                "apikey": self.api_key,
                "min_value": self.min_value_usd,
                "limit": 50,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(WHALE_ALERT_URL, params=params)
                resp.raise_for_status()
            data = resp.json()

            for tx in data.get("transactions", []):
                symbol = self._extract_symbol(tx)
                amount = tx.get("amount", 0)
                value_usd = tx.get("value_usd", 0)

                # Only create opportunity for significant movements
                if value_usd < self.min_value_usd:
                    continue

                from_to = f"{tx.get('from', {}).get('owner', 'unknown')} -> {tx.get('to', {}).get('owner', 'unknown')}"
                title = f"Whale Alert: {amount:.2f} {symbol} (${value_usd:,.0f})"

                content_hash = hashlib.md5(f"{tx.get('id', '')}".encode()).hexdigest()
                if content_hash in self._last_hashes:
                    continue

                self._last_hashes.add(content_hash)

                results.append(PollerResult(
                    source=self.source,
                    title=title,
                    description=f"Large transfer: {from_to}. Check for potential market impact.",
                    url=f"https://whale-alert.io/transaction/{tx.get('id', '')}",
                    symbol=f"{symbol}USDT" if symbol else None,
                    raw_data={"hash": content_hash, "transaction_id": tx.get("id")},
                ))

        except Exception as e:
            logger.error(f"WhaleAlertPoller fetch error: {e}")

        return results

    def _extract_symbol(self, tx: dict) -> Optional[str]:
        """Estrae il simbolo dalla transazione."""
        symbol = tx.get("symbol", "")
        if symbol:
            return symbol.replace("-", "").upper()  # ETH-USDT -> ETHUSDT
        return None

    def get_default_interval(self) -> int:
        """Polling ogni 5 minuti."""
        return 300