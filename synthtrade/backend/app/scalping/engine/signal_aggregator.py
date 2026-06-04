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
            )

        # In paper mode, se intelligence score è troppo basso o collector falliti,
        # usa solo il segnale tecnico (permette debug senza API esterne)
        if paper_mode and abs(market_score.total) < 5.0:
            if technical.confidence >= self._min_confidence:
                logger.info(
                    f"{YELLOW}📋 PAPER MODE: {technical.type} {symbol} @ {technical.confidence:.2f} "
                    f"(intelligence bypassed: score={market_score.total:.1f}){RESET}"
                )
                return ExecutionDecision(
                    execute=True,
                    confidence=technical.confidence,
                    reason=f"paper_mode fallback: {technical.type}@{technical.confidence:.2f}",
                )
            else:
                return ExecutionDecision(
                    execute=False,
                    reason=f"paper_mode: technical confidence {technical.confidence:.2f} < {self._min_confidence}",
                )

        # Se lo score non e' tradeable, blocca (solo in modalità normale)
        if not market_score.tradeable:
            reason = f"score intelligence {market_score.total:.1f} < soglia {market_score.signal_strength:.1f}"
            logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason} (bias={market_score.bias}){RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
            )

        # Verifica allineamento bias intelligence vs segnale tecnico
        bias = market_score.bias
        if bias == "bullish" and technical.type not in ("BUY",):
            reason = f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}"
            logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
            )
        if bias == "bearish" and technical.type not in ("SELL", "CLOSE"):
            reason = f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}"
            logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
            )
        if bias == "neutral":
            reason = "bias intelligence neutrale, no trade"
            logger.warning(f"{YELLOW}🟡 SKIP: {symbol} {reason} (score={market_score.total:.1f}){RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
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
        )
