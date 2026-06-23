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
import collections
from decimal import Decimal
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

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

    # Global registry per evitare istanze duplicate dello stesso simbolo
    _instances: Dict[str, "SignalScoreEngine"] = {}

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
        if not settings.scalping.SCALPING_WHALE_ENABLED:
            self.weights["whale"] = 0.0
        self.threshold = threshold

        # Istanzia collector
        self._funding_rate = FundingRateCollector(timeout_seconds=timeout)
        self._open_interest = OpenInterestCollector(timeout_seconds=timeout)
        self._long_short = LongShortRatioCollector(timeout_seconds=timeout)
        self._fear_greed = FearGreedCollector(timeout_seconds=timeout)
        self._sentiment = SentimentCollector(timeout_seconds=timeout)
        self._whale = WhaleCollector(timeout_seconds=timeout)
        self._onchain = OnChainCollector(timeout_seconds=timeout)
        
        # Buffer circolare in memory per gli ultimi 60 score (1 ora se snapshot = 1 min)
        self._score_history: collections.deque = collections.deque(maxlen=60)
        
        # CVDCalculator e' diverso: non fa chiamate HTTP, accumula trades
        self._cvd_calculator: Optional[CVDCalculator] = None

    @classmethod
    def get_or_create(
        cls,
        symbol: str = "BTCUSDT",
        weights: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        timeout: float = 10.0,
    ) -> "SignalScoreEngine":
        """Factory method: ritorna istanza singleton per simbolo.
        
        IMPORTANT: Il simbolo viene normalizzato in UPPERCASE per evitare
        duplicati per case mismatch (es. "bnbusdc" vs "BNBUSDC").
        
        Se una istanza per questo simbolo esiste già, la ritorna.
        Altrimenti crea una nuova e la registra nel global registry.
        """
        normalized = symbol.upper()
        if normalized not in cls._instances:
            cls._instances[normalized] = cls(
                symbol=symbol,  # Mantiene il case originale per compatibilità interna
                weights=weights,
                threshold=threshold,
                timeout=timeout
            )
            logger.info(f"[SignalScoreEngine] Created singleton instance for {normalized} (id={id(cls._instances[normalized])})")
        instance = cls._instances[normalized]
        logger.info(f"[SignalScoreEngine] get_or_create({symbol}) -> normalized={normalized} id={id(instance)}, cvd_calculator={instance._cvd_calculator is not None}")
        return instance

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
        from app.scalping.config_loader import get_scalping_config

        # Normalizza simbolo per collector futures: USDC → USDT
        # Binance Futures (funding rate, OI, long/short) usa solo USDT perpetual.
        # Per simboli come BNBUSDC, non esiste un perpetual USDC, quindi usiamo
        # i dati del perpetual USDT che rappresentano lo stesso sottostante (BNB).
        futures_symbol = self.symbol.upper().replace("USDC", "USDT")

        # Raccogli dati da tutti i collector in parallelo
        # Skip whale collector se disabilitato (peso 0.0)
        collector_tasks = [
            self._funding_rate.collect(futures_symbol),
            self._open_interest.collect(futures_symbol),
            self._long_short.collect(futures_symbol),
            self._fear_greed.collect(),
            self._sentiment.collect(self.symbol),
        ]
        if self.weights.get("whale", 0.0) > 0:
            collector_tasks.append(self._whale.collect(self.symbol))
        else:
            # Whale disabilitato: usa coroutine che ritorna None
            async def _disabled_whale():
                return None
            collector_tasks.append(_disabled_whale())
        
        collector_tasks.append(self._onchain.collect(self.symbol))
        
        try:
            results = await asyncio.gather(*collector_tasks, return_exceptions=True)
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
        
        # Whale disabilitato: forza None
        if self.weights.get("whale", 0.0) == 0.0:
            whale = None

        # Log dettagliato per debugging collector failures
        collector_status = {
            "funding_rate": "OK" if fr else ("ERROR" if isinstance(results[0], Exception) else "NONE"),
            "open_interest": "OK" if oi else ("ERROR" if isinstance(results[1], Exception) else "NONE"),
            "long_short_ratio": "OK" if ls_result else ("ERROR" if isinstance(results[2], Exception) else "NONE"),
            "fear_greed": "OK" if fg else ("ERROR" if isinstance(results[3], Exception) else "NONE"),
            "sentiment": "OK" if sent else ("ERROR" if isinstance(results[4], Exception) else "NONE"),
            "whale": "OK" if whale else ("ERROR" if isinstance(results[5], Exception) else "NONE"),
            "onchain": "OK" if onchain else ("ERROR" if isinstance(results[6], Exception) else "NONE"),
        }
        logger.debug(f"Collector status for {self.symbol}: {collector_status}")
        
        # Log errori specifici
        for i, (name, result) in enumerate(zip(["funding_rate", "open_interest", "long_short_ratio", "fear_greed", "sentiment", "whale", "onchain"], results)):
            if isinstance(result, Exception):
                logger.warning(f"{name} collector failed: {result}")

        # CVD dall'accumulatore interno (se collegato)
        # NOTA: CVD calculator viene collegato dal router via _set_cvd_calculator().
        # Se l'istanza è singleton (get_or_create), il CVD è condiviso tra pipeline e snapshot job.
        cvd_data = self._cvd_calculator.snapshot(self.symbol) if self._cvd_calculator else None
        if cvd_data is None:
            logger.debug(f"[ScoreEngine] CVD not available for {self.symbol} — calculator not wired or still initializing")

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

        # CVD — con periodo di grazia: salta CVD se il calculator è appena partito
        # (meno di 100 trades accumulati) per non falsare lo score con CVD=0
        trades_count = 0  # default per logging e grace period
        if cvd_data is not None:
            trades_count = getattr(self._cvd_calculator, '_trades_since_reset', 0) if self._cvd_calculator else 0
            if trades_count < 100 and self._cvd_calculator is not None:
                logger.debug(
                    f"[ScoreEngine] CVD grace period: only {trades_count} trades, "
                    f"excluding CVD from score to avoid bias"
                )
                # Non aggiungere CVD al breakdown né al weighted score
            else:
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
            fg_score = FearGreedCollector.value_to_score(fg.value)
            breakdown["fear_greed"] = round(fg_score, 2)
            weighted_score += fg_score * self.weights.get("fear_greed", 0.15)
            total_weight += self.weights.get("fear_greed", 0.15)

        # Sentiment
        if sent is not None:
            sent_score = SentimentCollector.sentiment_to_score(sent.score)
            breakdown["sentiment"] = round(sent_score, 2)
            weighted_score += sent_score * self.weights.get("sentiment", 0.05)
            total_weight += self.weights.get("sentiment", 0.05)

        # Whale Movements — includi nel peso SOLO se abbiamo attività reale
        # Se whale è None o recent_whale_activity=False, non distorcere la normalizzazione
        if whale is not None and whale.recent_whale_activity is True:
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

        # I collector restituiscono già un valore scalato [-100..+100]
        total = max(-100.0, min(100.0, round(normalized_score, 1)))

        # Determina bias e tradeable — soglia letta da config loader runtime (aggiornabile da Supervisor)
        # NOTA: la soglia viene riletta a ogni get_snapshot() dal config loader, che fa merge
        # settings.env + override DB. Questo permette al Supervisor di modificare la soglia
        # a caldo tramite update_threshold senza restart del backend.
        config_loader = get_scalping_config()
        runtime_threshold = config_loader.signal_strength_threshold  # default settings 15.0, override DB
        
        total_weight_configured = sum(w for w in self.weights.values() if w > 0)
        coverage = total_weight / total_weight_configured if total_weight_configured > 0 else 0.0
        
        # Gate 1: Skip se coverage insufficiente (meno del 50% dei dati disponibili)
        if coverage < 0.5:
            bias = "neutral"
            tradeable = False
            effective_threshold = runtime_threshold  # per debug log
        else:
            # Gate 2: Soglia da config loader (modificabile dal Supervisor a runtime)
            # Lo score deve davvero superare la soglia per essere valido
            effective_threshold = runtime_threshold  
            
            if total >= effective_threshold:
                bias = "bullish"
            elif total <= -effective_threshold:
                bias = "bearish"
            else:
                bias = "neutral"
            
            tradeable = abs(total) >= effective_threshold and bias != "neutral"

        # DEBUG: log dettagliato per diagnosticare scala reale dei collector
        logger.debug(
            "[ScoreEngine DEBUG] id=%s raw_scores=%s | weighted_sum=%.4f | total_weight=%.4f | "
            "weighted_avg=%.4f | coverage=%.4f (%.0f%%) | threshold_configured=%.4f | "
            "final_total=%.1f | bias=%s | tradeable=%s | cvd_trades=%s",
            id(self),
            {k: round(v, 4) for k, v in breakdown.items()},
            weighted_score,
            total_weight,
            normalized_score,
            coverage,
            coverage * 100,
            self.threshold,
            total,
            bias,
            tradeable,
            trades_count if cvd_data is not None else "N/A",
        )

        logger.debug(
            f"[ScoreEngine] id={id(self)} {self.symbol} total={total:.1f} "
            f"coverage={coverage:.2f} eff_threshold={effective_threshold:.1f} "
            f"bias={bias} tradeable={tradeable} "
            f"collectors={list(breakdown.keys())} "
            f"cvd_wired={self._cvd_calculator is not None}"
        )

        computed_at = datetime.now(timezone.utc)
        
        # Salva in memory history
        self._score_history.append((computed_at, total))
        
        # Calcola trend
        trend_5m, velocity, trend_direction = self._calculate_trend(computed_at)

        signal_score = SignalScore(
            total=total,
            bias=bias,
            tradeable=tradeable,
            breakdown=breakdown,
            signal_strength=abs(total),
            trend_5m=trend_5m,
            velocity=velocity,
            trend_direction=trend_direction,
            symbol=self.symbol,
            computed_at=computed_at
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

    def _calculate_trend(self, now: datetime) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Calcola trend, velocity e direction basandosi sulla history in RAM degli ultimi 5 min."""
        if len(self._score_history) < 2:
            return None, None, None
            
        current_score = self._score_history[-1][1]
        
        # Trova lo score di circa 5 minuti fa (cerca indietro)
        past_score = None
        for timestamp, score in reversed(self._score_history):
            delta_seconds = (now - timestamp).total_seconds()
            # Prendiamo il primo score che sia vecchio di almeno 4 minuti (fino a 6 max)
            if delta_seconds >= 240:
                past_score = score
                break
                
        if past_score is None:
            # Rimuoviamo il fallback (come suggerito dalla review).
            # Se la sessione è appena partita e non abbiamo dati di almeno 4 minuti fa, 
            # non falsifichiamo la velocity calcolandola su una finestra troppo corta.
            return None, None, None
            
        trend_5m = round(current_score - past_score, 2)
        velocity = round(trend_5m / 5.0, 2)
        
        # Direction: converging (verso lo zero), diverging (si allontana dallo zero), stable (variazione minima)
        if abs(trend_5m) < 0.5:
            trend_direction = "stable"
        else:
            # Sta andando verso 0?
            if abs(current_score) < abs(past_score):
                trend_direction = "converging"
            else:
                trend_direction = "diverging"
                
        return trend_5m, velocity, trend_direction