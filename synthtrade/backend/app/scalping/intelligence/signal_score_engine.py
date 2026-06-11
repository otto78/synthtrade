"""SignalScoreEngine — aggrega tutti i collector in uno score normalizzato.

Pesi configurabili (somma = 1.0):
  funding_rate:     0.20  (segnale contrarian affidabile)
  cvd:              0.20  (pressione reale di mercato)
  open_interest:    0.15  (contesto esposizione)
  long_short_ratio: 0.15  (sentiment contrarian futures)
  fear_greed:       0.15  (contesto macro psicologico)
  whale:            0.10  (movimenti on-chain massicci)
  sentiment:        0.05  (news, rumoroso su simboli non-BTC/ETH)
  onchain:          0.0   (escluso: richiede Dune query IDs)

Il SignalScoreEngine:
  1. Chiama ogni collector in parallelo
  2. Converte ogni dato grezzo in contributo score tramite metodi statici dei collector
  3. Applica pesatura normalizzata
  4. Determina bias e tradeable basandosi sulla soglia configurata, scalata dinamicamente
     in base al numero di collector che hanno effettivamente risposto (coverage).
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)

from app.scalping.models.intelligence import (
    CVDData,
    FearGreedData,
    FundingRate,
    LongShortRatio,
    OpenInterest,
    OnChainData,
    SentimentData,
    WhaleData,
    SignalScore,
    MarketIntelSnapshot,
)
from app.scalping.intelligence.collectors.funding_rate import FundingRateCollector
from app.scalping.intelligence.collectors.open_interest import OpenInterestCollector
from app.scalping.intelligence.collectors.long_short_ratio import LongShortRatioCollector
from app.scalping.intelligence.collectors.fear_greed import FearGreedCollector
from app.scalping.intelligence.collectors.cvd_calculator import CVDCalculator
from app.scalping.intelligence.collectors.sentiment import SentimentCollector
from app.scalping.intelligence.collectors.whale import WhaleCollector
from app.scalping.intelligence.collectors.onchain import OnChainCollector
from app.config import settings

# Pesi normalizzati per ogni fonte (somma = 1.0)
# OnChain rimosso (richiede Dune query IDs, non utile per scalping intraday)
# Sentiment ridotto perche' rumoroso su simboli non-BTC/ETH
DEFAULT_WEIGHTS: Dict[str, float] = {
    "funding_rate": 0.20,
    "cvd": 0.20,
    "open_interest": 0.15,
    "long_short_ratio": 0.15,
    "fear_greed": 0.15,
    "whale": 0.10,
    "sentiment": 0.05,
    "onchain": 0.0,
}


class SignalScoreEngine:
    """Motore di scoring intelligence.

    Aggrega i dati di tutti i collector e produce uno score
    normalizzato da -100 (bearish) a +100 (bullish).

    Uso:
        engine = SignalScoreEngine(symbol="BTCUSDT")
        score = await engine.compute()
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        weights: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        timeout: float = 10.0,
    ):
        if threshold is None:
            threshold = settings.scalping.SCALPING_SIGNAL_STRENGTH_THRESHOLD
        self.symbol = symbol
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.threshold = threshold

        # Istanzia collector
        self._funding_rate = FundingRateCollector(timeout_seconds=timeout)
        self._open_interest = OpenInterestCollector(timeout_seconds=timeout)
        self._long_short = LongShortRatioCollector(timeout_seconds=timeout)
        self._fear_greed = FearGreedCollector(timeout_seconds=timeout)
        self._sentiment = SentimentCollector(timeout_seconds=timeout)
        self._whale = WhaleCollector(timeout_seconds=timeout)
        self._onchain = OnChainCollector(timeout_seconds=timeout)
        
        # CVDCalculator e' diverso: non fa chiamate HTTP, accumula trades
        self._cvd_calculator: Optional[CVDCalculator] = None

    def _set_cvd_calculator(self, calculator: CVDCalculator) -> None:
        """Collega un CVDCalculator esterno (alimentato dal WS client)."""
        self._cvd_calculator = calculator

    async def compute(self) -> SignalScore:
        """Calcola lo score intelligence aggregato per il simbolo.

        Returns:
            SignalScore con total, bias, tradeable, breakdown.
        """
        snapshot = await self.get_snapshot()
        if snapshot.signal_score is None:
            # Fallback in caso di errore critico, non dovrebbe accadere
            from datetime import datetime, timezone
            return SignalScore(
                total=0.0,
                bias="neutral",
                tradeable=False,
                symbol=self.symbol,
                computed_at=datetime.now(timezone.utc)
            )
        return snapshot.signal_score

    async def get_snapshot(self) -> MarketIntelSnapshot:
        """Raccoglie tutti i dati e calcola lo score, restituendo uno snapshot completo.

        Returns:
            MarketIntelSnapshot con dati grezzi e score.
        """
        from datetime import datetime, timezone
        from typing import cast
        from app.scalping.models.intelligence import (
            MarketIntelSnapshot, FundingRate, OpenInterest, LongShortRatio, 
            FearGreedData, SentimentData, WhaleData, OnChainData
        )

        # Normalizza simbolo per collector futures: USDC → USDT
        # Binance Futures (funding rate, OI, long/short) usa solo USDT perpetual.
        # Per simboli come BNBUSDC, non esiste un perpetual USDC, quindi usiamo
        # i dati del perpetual USDT che rappresentano lo stesso sottostante (BNB).
        futures_symbol = self.symbol.upper().replace("USDC", "USDT")

        # Raccogli dati da tutti i collector in parallelo
        try:
            results = await asyncio.gather(
                self._funding_rate.collect(futures_symbol),
                self._open_interest.collect(futures_symbol),
                self._long_short.collect(futures_symbol),
                self._fear_greed.collect(),
                self._sentiment.collect(self.symbol),
                self._whale.collect(self.symbol),
                self._onchain.collect(self.symbol),
                return_exceptions=True
            )
        except asyncio.CancelledError:
            logger.debug("get_snapshot cancelled (shutdown)")
            return MarketIntelSnapshot(symbol=self.symbol)

        # Estrai e casta i risultati (asyncio.gather restituisce una lista)
        # return_exceptions=True significa che ogni elemento può essere l'oggetto atteso o un'eccezione
        
        fr = results[0] if isinstance(results[0], FundingRate) else None
        oi = results[1] if isinstance(results[1], OpenInterest) else None
        ls_result = results[2] if isinstance(results[2], LongShortRatio) else None
        fg = results[3] if isinstance(results[3], FearGreedData) else None
        sent = results[4] if isinstance(results[4], SentimentData) else None
        whale = results[5] if isinstance(results[5], WhaleData) else None
        onchain = results[6] if isinstance(results[6], OnChainData) else None

        # CVD dall'accumulatore interno (se collegato)
        cvd_data = self._cvd_calculator.snapshot(self.symbol) if self._cvd_calculator else None

        # Calcola contributi individuali
        breakdown: Dict[str, float] = {}
        weighted_score = 0.0
        total_weight = 0.0

        # Funding Rate
        if fr is not None:
            fr_score = FundingRateCollector.rate_to_score(fr.rate)
            breakdown["funding_rate"] = round(fr_score, 2)
            weighted_score += fr_score * self.weights.get("funding_rate", 0.20)
            total_weight += self.weights.get("funding_rate", 0.20)

        # CVD
        if cvd_data is not None:
            cvd_score = CVDCalculator.cvd_to_score(
                cvd_data.cvd, Decimal("1000")
            )
            breakdown["cvd"] = round(cvd_score, 2)
            weighted_score += cvd_score * self.weights.get("cvd", 0.20)
            total_weight += self.weights.get("cvd", 0.20)

        # Open Interest — usa baseline rolling dinamica invece di valore fisso
        if oi is not None:
            baseline = self._open_interest.get_baseline(futures_symbol)
            if baseline == 0:
                # Prima chiamata: usa il valore corrente come baseline (score = 0, neutro)
                baseline = oi.value_usd
            oi_score = OpenInterestCollector.oi_to_score(oi.value_usd, baseline)
            breakdown["open_interest"] = round(oi_score, 2)
            weighted_score += oi_score * self.weights.get("open_interest", 0.15)
            total_weight += self.weights.get("open_interest", 0.15)

        # Long/Short Ratio
        if ls_result is not None:
            ls_score = LongShortRatioCollector.ratio_to_score(ls_result.long_pct)
            breakdown["long_short_ratio"] = round(ls_score, 2)
            weighted_score += ls_score * self.weights.get("long_short_ratio", 0.15)
            total_weight += self.weights.get("long_short_ratio", 0.15)

        # Fear & Greed
        if fg is not None:
            fg_score = FearGreedCollector.fng_to_score(fg.value)
            breakdown["fear_greed"] = round(fg_score, 2)
            weighted_score += fg_score * self.weights.get("fear_greed", 0.15)
            total_weight += self.weights.get("fear_greed", 0.15)

        # Sentiment
        if sent is not None:
            sent_score = SentimentCollector.sentiment_to_score(sent.score)
            breakdown["sentiment"] = round(sent_score, 2)
            weighted_score += sent_score * self.weights.get("sentiment", 0.05)
            total_weight += self.weights.get("sentiment", 0.05)

        # Whale Movements — includi nel peso SOLO se abbiamo dati reali (not None)
        # Se whale è None (nessuna sorgente ha risposto), non distorcere la normalizzazione
        if whale is not None and whale.recent_whale_activity is not None:
            whale_score = WhaleCollector.whale_to_score(whale)
            breakdown["whale"] = round(whale_score, 2)
            weighted_score += whale_score * self.weights.get("whale", 0.10)
            total_weight += self.weights.get("whale", 0.10)

        # On-Chain (peso 0.0, escluso da coverage ma raccolto se data disponibile)
        if onchain is not None:
            onchain_score = OnChainCollector.onchain_to_score(onchain)
            breakdown["onchain"] = round(onchain_score, 2)
            # Peso 0.0: non contribuisce a weighted_score ne' a total_weight

        # Normalizza lo score se non tutti i collector hanno risposto
        if total_weight > 0:
            normalized_score = weighted_score / total_weight
        else:
            normalized_score = 0.0

        # Scala da [-25..+25] a [-100..+100]
        total = normalized_score * 4.0
        total = max(-100.0, min(100.0, round(total, 1)))

        # Determina bias con soglia scalata alla coverage dei collector
        # coverage = somma pesi collector che hanno risposto (0..1)
        # Con coverage=1.0 (tutti): soglia=threshold
        # Con coverage=0.30 (3 collector): soglia=threshold * 0.30 = ~4.5
        coverage = total_weight  # total_weight è la somma dei pesi dei collector che hanno risposto
        effective_threshold = self.threshold * coverage

        if total >= effective_threshold:
            bias = "bullish"
        elif total <= -effective_threshold:
            bias = "bearish"
        else:
            bias = "neutral"

        # Tradeable con la stessa soglia scalata
        tradeable = abs(total) >= effective_threshold and bias != "neutral"

        logger.debug(
            f"[ScoreEngine] {self.symbol} total={total:.1f} "
            f"coverage={coverage:.2f} eff_threshold={effective_threshold:.1f} "
            f"bias={bias} tradeable={tradeable} "
            f"collectors={list(breakdown.keys())}"
        )

        signal_score = SignalScore(
            total=total,
            bias=bias,
            tradeable=tradeable,
            breakdown=breakdown,
            signal_strength=abs(total),
            symbol=self.symbol,
            computed_at=datetime.now(timezone.utc)
        )

        return MarketIntelSnapshot(
            symbol=self.symbol,
            funding_rate=fr,
            open_interest=oi,
            long_short_ratio=ls_result,
            cvd=cvd_data,
            fear_greed=fg,
            sentiment=sent,
            whale=whale,
            onchain=onchain,
            signal_score=signal_score,
            snapshot_at=signal_score.computed_at
        )