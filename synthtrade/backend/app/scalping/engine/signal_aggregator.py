"""SignalAggregator — combina seganle intelligence + segnale tecnico.

Secondo l'architettura v2.0:
  "Un ordine viene eseguito SOLO se entrambi sono allineati:
   - Score intelligence > soglia (default: 30)
   - Strategia tecnica conferma (filtro timing)"
"""

from dataclasses import dataclass
from typing import Optional

from app.scalping.models.intelligence import SignalScore


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
        aggregator = SignalAggregator(min_confidence=0.6)
        score = await engine.compute()  # SignalScore
        signal = TechnicalSignal(type='BUY', confidence=0.8)
        decision = aggregator.should_execute(signal, score)
    """

    def __init__(self, min_confidence: float = 0.6):
        self._min_confidence = min_confidence

    def should_execute(
        self,
        technical: TechnicalSignal,
        market_score: SignalScore,
    ) -> ExecutionDecision:
        """Decide se eseguire un ordine basandosi su intelligence + tecnico.

        Args:
            technical: Segnale tecnico dalla strategia attiva.
            market_score: Score intelligence dal SignalScoreEngine.

        Returns:
            ExecutionDecision con execute=True/False e motivazione.
        """
        # Se il technical e' NONE, non fare nulla
        if technical.type == "NONE":
            return ExecutionDecision(
                execute=False,
                reason="nessun segnale tecnico",
            )

        # Se lo score non e' tradeable, blocca
        if not market_score.tradeable:
            return ExecutionDecision(
                execute=False,
                reason=f"score intelligence {market_score.total:.1f} sotto soglia {market_score.signal_strength:.1f}",
            )

        # Verifica allineamento bias intelligence vs segnale tecnico
        bias = market_score.bias
        if bias == "bullish" and technical.type not in ("BUY",):
            return ExecutionDecision(
                execute=False,
                reason=f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}",
            )
        if bias == "bearish" and technical.type not in ("SELL", "CLOSE"):
            return ExecutionDecision(
                execute=False,
                reason=f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}",
            )
        if bias == "neutral":
            return ExecutionDecision(
                execute=False,
                reason="bias intelligence neutrale, no trade",
            )

        # Calcola confidenza combinata (media di signal_strength normalizzato + technical confidence)
        signal_norm = (market_score.signal_strength or 0.0) / 100.0  # 0..1
        combined = (signal_norm + technical.confidence) / 2.0

        if combined < self._min_confidence:
            return ExecutionDecision(
                execute=False,
                reason=f"confidenza combinata {combined:.2f} < soglia {self._min_confidence}",
            )

        return ExecutionDecision(
            execute=True,
            confidence=round(combined, 3),
            reason=f"intelligence={market_score.total:.1f} ({market_score.bias}) + tecnico={technical.type}@{technical.confidence:.2f}",
        )