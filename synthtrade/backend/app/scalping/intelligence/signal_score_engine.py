"""SignalScoreEngine — aggrega tutti i collector in uno score normalizzato.

<<<<<<< Updated upstream
Pesi configurabili (relativi; somma non vincolata a 1.0 — l'engine normalizza):
=======
Pesi configurabili (somma = 1.0):
>>>>>>> Stashed changes
  funding_rate:     0.20  (segnale contrarian affidabile)
  cvd:              0.20  (pressione reale di mercato)
  open_interest:    0.15  (contesto esposizione)
  long_short_ratio: 0.15  (sentiment contrarian futures)
  fear_greed:       0.15  (contesto macro psicologico)
  whale:            0.10  (movimenti on-chain massicci)
  sentiment:        0.05  (news, rumoroso su simboli non-BTC/ETH)
  onchain:          0.0   (escluso: richiede Dune query IDs)
<<<<<<< Updated upstream
  order_book_imbalance: 0.15  (TASK-1151, peso provvisorio; da ricalibrare in Fase 6)
=======
>>>>>>> Stashed changes

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
import time
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
    OrderBookImbalance,
    SpreadSnapshot,
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
from app.scalping.intelligence.collectors.order_book_imbalance import OrderBookImbalanceCollector
from app.scalping.intelligence.collectors.spread import SpreadCollector
from app.config import settings

<<<<<<< Updated upstream
# Pesi normalizzati per ogni fonte (relativi; la somma NON deve essere 1.0).
# OnChain rimosso (richiede Dune query IDs, non utile per scalping intraday)
# Sentiment ridotto perche' rumoroso su simboli non-BTC/ETH
# order_book_imbalance aggiunto in TASK-1151 con peso provvisorio (da ricalibrare in Fase 6).
# NOTA: i pesi sono relativi; l'engine normalizza dividendo per il total_weight risposto,
# quindi aggiungere un peso provvisorio > 1.0 non altera il contributo dei collector esistenti.
=======
# Pesi normalizzati per ogni fonte (somma = 1.0)
# OnChain rimosso (richiede Dune query IDs, non utile per scalping intraday)
# Sentiment ridotto perche' rumoroso su simboli non-BTC/ETH
>>>>>>> Stashed changes
DEFAULT_WEIGHTS: Dict[str, float] = {
    "funding_rate": 0.20,
    "cvd": 0.20,
    "open_interest": 0.15,
    "long_short_ratio": 0.15,
    "fear_greed": 0.15,
    "whale": 0.10,
    "sentiment": 0.05,
    "onchain": 0.0,
<<<<<<< Updated upstream
    "order_book_imbalance": 0.15,  # TASK-1151 (peso provvisorio)
=======
>>>>>>> Stashed changes
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
        adapter: Optional[object] = None,
    ):
        if threshold is None:
            threshold = settings.scalping.SCALPING_SIGNAL_STRENGTH_THRESHOLD
        self.symbol = symbol
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        if not settings.scalping.SCALPING_WHALE_ENABLED:
            self.weights["whale"] = 0.0
        self.threshold = threshold

        # Adapter provider-aware (TASK-1153): passato ai 3 collector futures
        # (funding_rate/open_interest/long_short) per usare endpoint nativi OKX
        # invece di Binance quando EXCHANGE_PROVIDER=okx.
        self._adapter = adapter

        # Istanzia collector
        self._funding_rate = FundingRateCollector(timeout_seconds=timeout, adapter=adapter)
        self._open_interest = OpenInterestCollector(timeout_seconds=timeout, adapter=adapter)
        self._long_short = LongShortRatioCollector(timeout_seconds=timeout, adapter=adapter)
        self._fear_greed = FearGreedCollector(timeout_seconds=timeout)
        self._sentiment = SentimentCollector(timeout_seconds=timeout)
        self._whale = WhaleCollector(timeout_seconds=timeout)
        self._onchain = OnChainCollector(timeout_seconds=timeout)
        self._order_book_imbalance = OrderBookImbalanceCollector(timeout_seconds=timeout)
        # TASK-1152: SpreadCollector attivo e loggato, ma NON cablato nel punteggio
        # (wiring OFF). Il risultato viene usato solo per il diagnostico.
        self._spread = SpreadCollector(timeout_seconds=timeout)
        
        # Buffer circolare in memory per gli ultimi 60 score (1 ora se snapshot = 1 min)
        self._score_history: collections.deque = collections.deque(maxlen=60)
        
        # CVDCalculator e' diverso: non fa chiamate HTTP, accumula trades
        self._cvd_calculator: Optional[CVDCalculator] = None

        # Cache snapshot: evita refetch HTTP ad ogni candela chiusa
        self._cached_snapshot: Optional[MarketIntelSnapshot] = None
        self._cached_at: float = 0.0

    @classmethod
    def get_or_create(
        cls,
        symbol: str = "BTCUSDT",
        weights: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        timeout: float = 10.0,
        adapter: Optional[object] = None,
    ) -> "SignalScoreEngine":
        """Factory method: ritorna istanza singleton per simbolo.
        
        IMPORTANT: Il simbolo viene normalizzato in UPPERCASE per evitare
        duplicati per case mismatch (es. "bnbusdc" vs "BNBUSDC").
        
        Se una istanza per questo simbolo esiste già, la ritorna.
        Altrimenti crea una nuova e la registra nel global registry.

        TASK-1153: se `adapter` non è fornito e `EXCHANGE_PROVIDER == "okx"`,
        risolve l'adapter nativo via exchange factory così i 3 collector futures
        (funding_rate/open_interest/long_short) chiamano endpoint OKX invece di
        Binance. In caso di errore di risoluzione, degrada a None (fallback
        legacy Binance) senza rompere lo scoring.
        """
        normalized = symbol.upper()
        if normalized not in cls._instances:
            if adapter is None and settings.EXCHANGE_PROVIDER.lower() == "okx":
                try:
                    from app.core.exchange_factory import get_adapter
                    adapter = get_adapter()
                except Exception as e:
                    logger.warning(
                        "SignalScoreEngine: adapter resolution failed (futures collectors "
                        "fall back to Binance legacy): %s",
                        e,
                    )
                    adapter = None
            cls._instances[normalized] = cls(
                symbol=symbol,  # Mantiene il case originale per compatibilità interna
                weights=weights,
                threshold=threshold,
                timeout=timeout,
                adapter=adapter,
            )
            logger.info(f"[SignalScoreEngine] Created singleton instance for {normalized} (id={id(cls._instances[normalized])})")
        instance = cls._instances[normalized]
        logger.info(f"[SignalScoreEngine] get_or_create({symbol}) -> normalized={normalized} id={id(instance)}, cvd_calculator={instance._cvd_calculator is not None}")
        return instance

    def _set_cvd_calculator(self, calculator: CVDCalculator) -> None:
        """Collega un CVDCalculator esterno (alimentato dal WS client)."""
        self._cvd_calculator = calculator

    def get_configurable_weight_total(self, symbol: str) -> tuple[float, list[str]]:
        """Calcola il peso configurabile totale per questo simbolo.

        Esclude dal denominatore:
        - whale, se SCALPING_WHALE_ENABLED=False
        - funding_rate/open_interest/long_short_ratio, se
          is_symbol_supported(symbol) == False per quel collector

        Ritorna (peso_totale_configurabile, lista_nomi_esclusi_strutturalmente)
        """
        weights = dict(self.weights)  # copia dei pesi runtime
        excluded: list[str] = []

        collectors_to_check = [
            ("funding_rate", self._funding_rate),
            ("open_interest", self._open_interest),
            ("long_short_ratio", self._long_short),
        ]
        for name, collector in collectors_to_check:
            if hasattr(collector, "is_symbol_supported"):
                if not collector.is_symbol_supported(symbol):
                    weights.pop(name, None)
                    excluded.append(name)

        return sum(weights.values()), excluded

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

    def _cache_ttl_sec(self) -> float:
        return float(settings.scalping.SCALPING_INTEL_UPDATE_INTERVAL_SEC)

    def _is_cache_valid(self) -> bool:
        if self._cached_snapshot is None:
            return False
        return (time.monotonic() - self._cached_at) < self._cache_ttl_sec()

    async def get_snapshot(self, force_refresh: bool = False) -> MarketIntelSnapshot:
        """Raccoglie tutti i dati e calcola lo score, restituendo uno snapshot completo.

        Args:
            force_refresh: Se True, ignora la cache e raccoglie dati freschi (es. intel job).

        Returns:
            MarketIntelSnapshot con dati grezzi e score.
        """
        if not force_refresh and self._is_cache_valid():
            logger.debug("[ScoreEngine] snapshot cache hit for %s", self.symbol)
            return self._cached_snapshot

        snapshot = await self._build_snapshot()
        self._cached_snapshot = snapshot
        self._cached_at = time.monotonic()
        return snapshot

    async def _build_snapshot(self) -> MarketIntelSnapshot:
        """Raccoglie dati dai collector e costruisce uno snapshot (senza cache)."""
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

        # Normalizza simbolo per collector futures: USDC → USDT
        # Binance Futures (funding rate, OI, long/short) usa solo USDT perpetual
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
        # OrderBookImbalance: sempre attivo (peso > 0) e supportato su ogni spot OKX
        collector_tasks.append(self._order_book_imbalance.collect(self.symbol))
        # Spread: collector chiamato per il diagnostico (TASK-1152, wiring OFF).
        # Il risultato (results[8]) NON entra nello score, ma compare nella lista
        # dei collector per verificarne il funzionamento a colpo d'occhio.
        collector_tasks.append(self._spread.collect(self.symbol))

        try:
<<<<<<< Updated upstream
            results = await asyncio.gather(*collector_tasks, return_exceptions=True)
=======
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
>>>>>>> Stashed changes
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
        obi = results[7] if isinstance(results[7], OrderBookImbalance) else None

        # Whale disabilitato: forza None
        if self.weights.get("whale", 0.0) == 0.0:
            whale = None

        # ──────────────────────────────────────────────────────────────
        # DIAGNOSTICO COLLECTOR — formato multi-riga (UNO per collector)
        # Temporaneo (TASK-1152): piu' leggibile a colpo d'occhio tra i log.
        # Da ricompattare in unica riga quando il debug non serve piu'.
        # ──────────────────────────────────────────────────────────────
        _diag = [
            ("funding_rate", self._funding_rate.is_symbol_supported(self.symbol), results[0]),
            ("open_interest", self._open_interest.is_symbol_supported(self.symbol), results[1]),
            ("long_short_ratio", self._long_short.is_symbol_supported(self.symbol), results[2]),
            ("fear_greed", True, results[3]),
            ("sentiment", True, results[4]),
            ("whale", self.weights.get("whale", 0.0) > 0.0, results[5]),
            ("onchain", True, results[6]),
            ("order_book_imbalance", True, results[7]),
            # Spread: collector attivo e loggato ma NON cablato nel punteggio
            # (TASK-1152 wiring OFF). Compare in lista per verificarne il
            # funzionamento, senza influenzare lo score.
            ("spread", True, results[8]),
        ]
        for _name, _active, _res in _diag:
            if isinstance(_res, Exception):
                _status = "ERROR"
            elif _res is None:
                _status = "NONE"
            else:
                _status = "OK"
            logger.info(
                "[COLLECTORS_DIAG_TEMP] symbol=%-10s | collector=%-20s | active=%-3s | status=%s",
                self.symbol, _name, "on" if _active else "off", _status,
            )

        _cvd_snap = self._cvd_calculator.snapshot(self.symbol) if self._cvd_calculator else None
        logger.info(
            "[COLLECTORS_DIAG_TEMP] symbol=%-10s | collector=%-20s | active=%-3s | status=%s",
            self.symbol, "cvd", "on" if self._cvd_calculator is not None else "off",
            "OK" if _cvd_snap is not None else "NONE",
        )

        # Log errori specifici (incl. spread, index 8)
        _all_names = [
            "funding_rate", "open_interest", "long_short_ratio", "fear_greed",
            "sentiment", "whale", "onchain", "order_book_imbalance", "spread",
        ]
        for i, name in enumerate(_all_names):
            if i < len(results) and isinstance(results[i], Exception):
                logger.warning(f"{name} collector failed: {results[i]}")

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
<<<<<<< Updated upstream
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
=======
            cvd_score = CVDCalculator.cvd_to_score(
                cvd_data.cvd, Decimal("1000")
            )
            breakdown["cvd"] = round(cvd_score, 2)
            weighted_score += cvd_score * self.weights.get("cvd", 0.20)
            total_weight += self.weights.get("cvd", 0.20)
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream

        # Order Book Imbalance — sempre supportato su spot OKX (incluso OKB-EUR)
        if obi is not None:
            obi_score = OrderBookImbalanceCollector.imbalance_to_score(obi.imbalance)
            breakdown["order_book_imbalance"] = round(obi_score, 2)
            weighted_score += obi_score * self.weights.get("order_book_imbalance", 0.15)
            total_weight += self.weights.get("order_book_imbalance", 0.15)
=======
>>>>>>> Stashed changes

        # Normalizza lo score se non tutti i collector hanno risposto
        if total_weight > 0:
            normalized_score = weighted_score / total_weight
        else:
            normalized_score = 0.0

        # I collector restituiscono già un valore scalato [-100..+100]
        total = max(-100.0, min(100.0, round(normalized_score, 1)))

<<<<<<< Updated upstream
        # Determina bias e tradeable — soglia letta da config loader runtime (aggiornabile da Supervisor)
        # NOTA: la soglia viene riletta a ogni get_snapshot() dal config loader, che fa merge
        # settings.env + override DB. Questo permette al Supervisor di modificare la soglia
        # a caldo tramite update_threshold senza restart del backend.
        config_loader = get_scalping_config()
        runtime_threshold = config_loader.signal_strength_threshold  # default settings 15.0, override DB
        
        total_weight_configured = sum(w for w in self.weights.values() if w > 0)
        coverage = total_weight / total_weight_configured if total_weight_configured > 0 else 0.0

        # ── Log diagnostico COVERAGE_REAL (TASK-1125) ──
        # Calcola la coverage reale: peso dei collector che hanno risposto diviso
        # peso dei collector strutturalmente disponibili per QUESTO simbolo.
        # Esclude dal denominatore collector che non possono MAI rispondere
        # (es. funding_rate per OKB-EUR che non ha perpetual futures).
        configurable_total, structurally_excluded = self.get_configurable_weight_total(self.symbol)
        responded_names = set(k for k in breakdown)
        responded_weight = sum(self.weights.get(k, 0.0) for k in responded_names)
        real_coverage = responded_weight / configurable_total if configurable_total > 0 else 0.0

        no_response_transient = [
            k for k in self.weights
            if self.weights.get(k, 0.0) > 0  # solo pesi attivi (> 0.0)
            and k not in responded_names
            and k not in structurally_excluded
            and k != "onchain"  # onchain ha peso 0.0, ignorato
        ]

        logger.info(
            "[ScoreEngine][COVERAGE_REAL] symbol=%s configurable_total=%.2f "
            "responded_weight=%.2f real_coverage=%.1f%% "
            "structurally_unavailable=%s no_response_transient=%s "
            "old_coverage_field=%.1f%%",
            self.symbol, configurable_total, responded_weight,
            real_coverage * 100,
            structurally_excluded, no_response_transient,
            coverage * 100,
        )
        # ── Fine log diagnostico ──

        # Gate 1: Skip se coverage insufficiente (meno del 50% dei dati disponibili)
        if coverage < 0.5:
=======
        # Determina bias con soglia scalata alla coverage dei collector
        # coverage = somma pesi collector che hanno risposto (0..1)
        # Con coverage=1.0 (tutti): soglia=threshold
        # Con coverage=0.30 (3 collector): soglia=threshold * 0.30 = ~4.5
        coverage = total_weight
        effective_threshold = self.threshold * coverage

        if total >= effective_threshold:
            bias = "bullish"
        elif total <= -effective_threshold:
            bias = "bearish"
        else:
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
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
=======
        # Tradeable con la stessa soglia scalata
        tradeable = abs(total) >= effective_threshold and bias != "neutral"

        logger.debug(
            f"[ScoreEngine] {self.symbol} total={total:.1f} "
            f"coverage={coverage:.2f} eff_threshold={effective_threshold:.1f} "
            f"bias={bias} tradeable={tradeable} "
            f"collectors={list(breakdown.keys())}"
        )
>>>>>>> Stashed changes

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