"""LongShortRatioCollector — recupera Long/Short Ratio da Binance Futures API.

Documentazione API:
  GET /futures/data/globalLongShortAccountRatio
  https://binance-docs.github.io/apidocs/futures/en/#long-short-ratio

> 70% long  -> mercato esposto a short squeeze (contrarian short bias)
> 70% short -> mercato esposto a long squeeze (contrarian long bias)
"""

import asyncio
import collections
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.scalping.intelligence.collectors._provider_maps import (
    OKX_PERPETUAL_MAP,
    extract_base_asset,
)
from app.scalping.models.intelligence import LongShortRatio

BINANCE_LS_URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
logger = logging.getLogger(__name__)

# Mappa simboli spot → futures perpetual per collector
# EUR symbols non hanno equivalente su Binance Futures → None = graceful skip.
FUTURES_SYMBOL_MAP = {
    "BNBUSDC": "BNBUSDT",
    "BTCUSDC": "BTCUSDT",
    "ETHUSDC": "ETHUSDT",
    "BTCEUR": None,
    "BTC-EUR": None,
    "ETHEUR": None,
    "ETH-EUR": None,
    "SOLEUR": None,
    "SOL-EUR": None,
    "XRPEUR": None,
    "XRP-EUR": None,
    "OKBEUR": None,
    "OKB-EUR": None,
}


class LongShortRatioCollector:
    """Collettore Long/Short Ratio (Binance legacy + OKX provider-aware).

    TASK-1158 (2026-07-14): OKX HA l'endpoint rubik
    (`/api/v5/rubik/stat/contracts/long-short-account-ratio`, `ccy`) che ritorna
    un RATIO (long/short), non le % separate di Binance. Con provider OKX e adapter
    valorizzato, il collector mappa lo spot `OKB-EUR` → `ccy=OKB`, chiama l'endpoint
    e converte ratio→long/short% (`long_pct = ratio/(1+ratio)*100`).
    Con adapter=None il comportamento legacy Binance è invariato.
    """

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3, adapter: Optional[object] = None):
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._adapter = adapter
        # TASK-1262: storico letture DISTINTE per baseline dinamica.
        # I collector girano ogni SCALPING_INTEL_UPDATE_INTERVAL_SEC (60s) ma gli
        # endpoint espongono period="5m": senza dedupe ogni valore reale verrebbe
        # campionato 5 volte consecutive e il lookback coprirebbe 12 minuti di
        # cronometro invece delle 12 letture distinte (= ~60 min) previste dal task.
        self._history = collections.deque(maxlen=12)
        from app.scalping.intelligence.collectors.circuit_breaker import CollectorCircuitBreaker
        self._cb = CollectorCircuitBreaker("long_short_ratio")

    def is_symbol_supported(self, symbol: str) -> bool:
        """True se il simbolo può strutturalmente avere long/short ratio.

        OKX provider: il dato esiste solo per base asset con perpetual USDT-SWAP
        (vedi OKX_PERPETUAL_MAP). Per base asset non mappati ritorna False in
        modo conservativo.
        Legacy Binance: usa la stessa FUTURES_SYMBOL_MAP del collect(). Se il
        simbolo non è nella mappa, ritorna True in modo conservativo.
        """
        if self._adapter is not None and settings.EXCHANGE_PROVIDER.lower() == "okx":
            base = extract_base_asset(symbol.upper())
            if base in OKX_PERPETUAL_MAP:
                return OKX_PERPETUAL_MAP[base] is not None
            return False
        sym_upper = symbol.upper()
        if sym_upper not in FUTURES_SYMBOL_MAP:
            return True
        return FUTURES_SYMBOL_MAP[sym_upper] is not None

    async def collect(self, symbol: str = "BTCUSDT", period: str = "5m") -> Optional[LongShortRatio]:
        if not self._cb.is_available():
            return None

        # ── OKX provider-aware path (TASK-1158) ──
        if self._adapter is not None and settings.EXCHANGE_PROVIDER.lower() == "okx":
            base = extract_base_asset(symbol.upper())
            inst_id = OKX_PERPETUAL_MAP.get(base)
            if inst_id is None:
                logger.debug(
                    "LongShortRatioCollector: skipping %s (base=%s) — no OKX perpetual "
                    "(structurally_unavailable)",
                    symbol, base,
                )
                return None
            try:
                ratio = await self._adapter.get_long_short_ratio(base, period=period)
            except Exception as e:
                logger.warning("LongShortRatioCollector OKX fetch failed for %s: %s", symbol, e)
                self._cb.on_failure()
                ratio = None
            if ratio is None:
                return None

            # OKX returns a RATIO (long/short), not separate percentages.
            long_pct = Decimal(str(ratio)) / (Decimal("1") + Decimal(str(ratio))) * Decimal("100")
            short_pct = Decimal("100") - long_pct

            logger.debug(
                "LongShortRatio (okx_native) for %s: ratio=%.4f long=%.2f%% short=%.2f%% "
                "(proxy via %s)",
                symbol, float(ratio), float(long_pct), float(short_pct), inst_id,
            )

            self._cb.on_success()
            self._record_reading(float(long_pct))
            return LongShortRatio(
                symbol=symbol.upper(),
                long_pct=long_pct,
                short_pct=short_pct,
                timestamp=datetime.now(timezone.utc),
            )

        # ── Legacy Binance path (unchanged) ──
        # Mappa USDC → USDT per i futures perpetual
        futures_symbol = FUTURES_SYMBOL_MAP.get(symbol.upper(), symbol.upper())

        if futures_symbol is None:
            logger.debug(
                "LongShortRatioCollector: skipping %s — no Binance Futures equivalent (EUR pair)",
                symbol,
            )
            return None

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    params = {
                        "symbol": futures_symbol,
                        "period": period,
                        "limit": 1,
                    }
                    response = await client.get(BINANCE_LS_URL, params=params)
                    response.raise_for_status()

                    data = response.json()
                    if not data:
                        return None

                    entry = data[0]
                    long_val = Decimal(str(entry.get("longAccount", "0")))
                    short_val = Decimal(str(entry.get("shortAccount", "0")))
                    
                    logger.debug("Raw LS data for %s: long=%s, short=%s", symbol, long_val, short_val)

                    long_pct = long_val * 100
                    self._record_reading(float(long_pct))

                    self._cb.on_success()
                    return LongShortRatio(
                        symbol=symbol.upper(),
                        long_pct=long_pct,
                        short_pct=short_val * 100,
                        timestamp=datetime.fromtimestamp(entry.get("timestamp", 0) / 1000),
                    )

            except Exception as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                    continue
                logger.warning("LongShortRatioCollector error for %s: %s", symbol, e)
                self._cb.on_failure()
                return None

    def _record_reading(self, long_pct: float) -> None:
        """Accoda una lettura solo se è una lettura distinta.

        Il collector viene invocato ogni 60s ma l'endpoint restituisce la stessa
        candela da 5 minuti: accodare sempre duplicherebbe ogni valore reale.
        Con la dedupe il deque contiene letture uniche e il lookback di 12
        copre ~60 min di storia reale.
        """
        if self._history and abs(self._history[-1] - long_pct) < 1e-9:
            return
        self._history.append(long_pct)

    def get_baseline(self) -> Optional[float]:
        """Media delle letture *precedenti* a quella corrente.

        collect() accoda la lettura appena presa prima che l'engine chieda la
        baseline, quindi l'ultimo elemento dello storico e' per definizione il
        valore corrente: va escluso. Includerlo smorzerebbe il delta di un
        fattore N/(N+1) e un cambio di regime resterebbe invisibile.

        Ritorna None finche' non ci sono letture storiche utilizzabili.
        """
        if not self.has_baseline():
            return None
        previous = list(self._history)[:-1]
        return sum(previous) / len(previous)

    def has_baseline(self) -> bool:
        """True se esiste una baseline utilizzabile per lo score."""
        return len(self._history) >= 2

    @staticmethod
    def ratio_to_score(long_pct: Decimal, baseline: Optional[float] = None) -> float:
        """Converte il long % in contributo score (-100 a +100).

        TASK-1262: usa la variazione dell'LSR invece del valore assoluto.
        Il long_pct assoluto di BTC e' stazionario intorno al 49% (misurato su
        194 candele: score +2.1 medio, contributo +0.21 punti) e non distingue
        "oggi e' piu' long di ieri" dal semplice fatto che BTC e' sempre long.
        Il delta rispetto alla media recente e' l'unica informazione utile.

        - long% in crescita vs media -> piu' esposizione long -> score negativo
        - long% in calo   vs media -> long che scaricano    -> score positivo
        """
        long_val = float(long_pct)
        if baseline is None:
            # Nessuna baseline: il contributo non e' calcolabile. Il chiamante
            # (SignalScoreEngine) esclude il collector dal punteggio, quindi
            # restituire 0.0 qui e' solo una difesa per usi diretti.
            return 0.0

        diff = long_val - baseline
        # Saturazione a +/-5 punti percentuali: un'escursione di 5pp del long%
        # in un'ora e' un movimento forte, non rumore di micro-tick.
        score = -diff * 20.0
        return max(-100.0, min(100.0, score))
