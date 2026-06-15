"""SignalAggregator — combina segnale intelligence + segnale tecnico.

Secondo l'architettura v2.0:
  "Un ordine viene eseguito SOLO se entrambi sono allineati:
   - Score intelligence > soglia (default: 15)
   - Strategia tecnica conferma (filtro timing)"
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.scalping.models.intelligence import SignalScore

logger = logging.getLogger(__name__)

# ANSI color codes for logs
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


@dataclass(frozen=True)
class ExecutionDecision:
    """Decisione di esecuzione dopo aver aggregato intelligence + tecnico."""

    execute: bool
    confidence: float = 0.0
    reason: Optional[str] = None
    signal_type: str = ""  # BUY/SELL/CLONE dal segnale tecnico originale


@dataclass(frozen=True)
class TechnicalSignal:
    """Segnale tecnico semplificato proveniente da una strategia."""

    type: str  # 'BUY', 'SELL', 'CLOSE', 'NONE'
    confidence: float = 0.0  # 0.0 - 1.0
    source: Optional[str] = None  # 'ema_cross', 'rsi_bollinger', etc.


class SignalAggregator:
    """Aggregatore ibrido: intelligence + tecnico.

    Un ordine viene eseguito SOLO se:
      1. Lo score intelligence e' tradeable
      2. Il bias e' allineato al segnale tecnico
      3. La confidenza combinata > soglia minima

    Uso:
        aggregator = SignalAggregator(min_confidence=0.4)
        score = await engine.compute()  # SignalScore
        signal = TechnicalSignal(type='BUY', confidence=0.8)
        decision = aggregator.should_execute(signal, score)
    """

    def __init__(self, min_confidence: Optional[float] = None):
        if min_confidence is None:
            from app.config import settings
            min_confidence = settings.scalping.SCALPING_MIN_CONFIDENCE
        self._min_confidence = min_confidence

    def should_execute(
        self,
        technical: TechnicalSignal,
        market_score: SignalScore,
        symbol: str = "",
        paper_mode: bool = False,
    ) -> ExecutionDecision:
        """Decide se eseguire un ordine basandosi su intelligence + tecnico.

        Args:
            technical: Segnale tecnico dalla strategia attiva.
            market_score: Score intelligence dal SignalScoreEngine.
            symbol: Simbolo (per log).
            paper_mode: Se True, usa solo segnale tecnico (per debug/test).

        Returns:
            ExecutionDecision con execute=True/False e motivazione.
        """
        # Se il technical e' NONE, non fare nulla
        if technical.type == "NONE":
            return ExecutionDecision(
                execute=False,
                reason="nessun segnale tecnico",
                signal_type=technical.type,
            )

        # ── FIX-2026-06-12: CLOSE sempre permesso ──
        # Un segnale CLOSE significa "chiudi la posizione aperta". Non deve
        # essere filtrato dal bias intelligence perché è un'uscita, non un'apertura.
        # Se viene bloccato (es. bias bullish blocca CLOSE), la posizione rimane
        # aperta all'infinito e il trade non viene mai registrato come chiuso.
        if technical.type == "CLOSE":
            logger.info(
                f"{GREEN}🟢 CLOSE {symbol} sempre permesso (segnale di uscita, non filtrato da bias){RESET}"
            )
            return ExecutionDecision(
                execute=True,
                confidence=min(technical.confidence, 1.0),
                reason=f"close_signal: {technical.type}@{technical.confidence:.2f} (uscita sempre permessa)",
                signal_type=technical.type,
            )

        num_collectors_responded = len(market_score.breakdown) if market_score.breakdown else 0
        mode_label = "PAPER" if paper_mode else "LIVE"

        from app.scalping.config_loader import get_scalping_config
        min_collectors = get_scalping_config().min_collectors

        # ── Caso 1: POCHI COLLECTOR → bypass intelligence (mancanza dati) ──────────
        # In live mode, molti collector falliscono (funding_rate, open_interest, whale, etc.
        # richiedono API keys). Se < min_collectors hanno risposto, trattiamo lo score come
        # "no data" e usiamo solo il segnale tecnico.
        if num_collectors_responded < min_collectors:
            bypass_reason = f"score={market_score.total:.1f} ({num_collectors_responded} collectors)"
            if technical.confidence >= self._min_confidence:
                logger.info(
                    f"{YELLOW}📋 {mode_label} MODE: {technical.type} {symbol} @ {technical.confidence:.2f} "
                    f"(intelligence bypassed: {bypass_reason}){RESET}"
                )
                return ExecutionDecision(
                    execute=True,
                    confidence=technical.confidence,
                    reason=f"{mode_label.lower()}_mode fallback (no intel): {technical.type}@{technical.confidence:.2f}",
                    signal_type=technical.type,
                )
            else:
                return ExecutionDecision(
                    execute=False,
                    reason=f"{mode_label.lower()}_mode: technical confidence {technical.confidence:.2f} < {self._min_confidence}",
                    signal_type=technical.type,
                )

        # ── Caso 2: COLLECTOR SUFFICIENTI MA SCORE BASSO → BLOCCO (neutrale confermato) ──
        # Se 4+ collector hanno risposto e lo score totale è < 5.0, significa che i
        # dati di intelligence ci sono ma indicano neutralità. Non ha senso bypassare:
        # blocchiamo il trade perché il mercato è oggettivamente neutrale.
        if abs(market_score.total) < 5.0:
            reason = (
                f"intelligence neutrale "
                f"({num_collectors_responded} collectors, score={market_score.total:.1f})"
            )
            logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
            )

        # ── Caso 3: SCORE ≥ 5.0 → filtro intelligence completo ─────────────────────

        # Se lo score non e' tradeable, blocca (solo in modalità normale)
        if not market_score.tradeable:
            reason = f"score intelligence {market_score.total:.1f} < soglia {market_score.signal_strength:.1f}"
            logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason} (bias={market_score.bias}){RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
            )

        # ── Mean-reversion bypass per strategie ranging ──────────────────────
        # In regime ranging, strategie come rsi_bollinger generano SELL quando il
        # prezzo tocca la banda superiore di Bollinger (mean-reversion). Questo
        # non è uno short direzionale ma una chiusura del range. Bloccare questi
        # SELL perché il bias intelligence è bullish impedisce qualsiasi trade
        # in ranging — BNB sale, tocca BB superiore, genera SELL, ma viene bloccato.
        # Lo stesso vale per BUY su BB inferiore con bias bearish.
        MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")

        # Verifica allineamento bias intelligence vs segnale tecnico
        bias = market_score.bias
        if bias == "bullish" and technical.type not in ("BUY",):
            # Permetti SELL da mean-reversion in ranging (chiusura range, non short)
            if technical.type == "SELL" and technical.source and any(technical.source.startswith(s) for s in MEAN_REVERSION_STRATEGIES):
                logger.info(
                    f"⚡ MEAN-REVERSION SELL permesso (source={technical.source}) "
                    f"nonostante bias={bias} — chiusura range, non short direzionale"
                )
            else:
                reason = f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}"
                logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
                return ExecutionDecision(
                    execute=False,
                    reason=reason,
                    signal_type=technical.type,
                )
        if bias == "bearish" and technical.type not in ("SELL", "CLOSE"):
            # Permetti BUY da mean-reversion in ranging (chiusura range, non long)
            if technical.type == "BUY" and technical.source and any(technical.source.startswith(s) for s in MEAN_REVERSION_STRATEGIES):
                logger.info(
                    f"⚡ MEAN-REVERSION BUY permesso (source={technical.source}) "
                    f"nonostante bias={bias} — chiusura range, non long direzionale"
                )
            else:
                reason = f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}"
                logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
                return ExecutionDecision(
                    execute=False,
                    reason=reason,
                    signal_type=technical.type,
                )
        if bias == "neutral":
            reason = "bias intelligence neutrale, no trade"
            logger.warning(f"{YELLOW}🟡 SKIP: {symbol} {reason} (score={market_score.total:.1f}){RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
            )

        # Calcola confidenza combinata (media di signal_strength normalizzato + technical confidence)
        signal_norm = (market_score.signal_strength or 0.0) / 100.0  # 0..1
        combined = (signal_norm + technical.confidence) / 2.0

        if combined < self._min_confidence:
            reason = f"confidenza combinata {combined:.2f} < soglia {self._min_confidence}"
            logger.warning(f"{YELLOW}🟡 SKIP: {symbol} {reason}{RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
            )

        # TRADE ESEGUITO
        reason_str = f"intelligence={market_score.total:.1f} ({market_score.bias}) + tecnico={technical.type}@{technical.confidence:.2f}"
        logger.info(
            f"{GREEN}🟢 SIGNAL: {technical.type} {symbol} conf={combined:.3f} | {reason_str}{RESET}"
        )
        return ExecutionDecision(
            execute=True,
            confidence=round(combined, 3),
            reason=reason_str,
            signal_type=technical.type,
        )
