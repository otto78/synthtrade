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
    ta_patterns: Optional[dict] = None
    vol_anomaly: bool = False


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
        # min_confidence può essere passato per override (es. in test),
        # altrimenti viene letto runtime dal ConfigLoader (modificabile via DB)
        self._override_min_confidence = min_confidence

    def _get_min_confidence(self) -> float:
        """Legge la soglia di confidenza minima dal runtime config loader.

        Se è stato passato un override (costruttore o test), usa quello.
        Altrimenti legge dal ConfigLoader che merge .env + DB override.
        """
        if self._override_min_confidence is not None:
            return self._override_min_confidence
        try:
            from app.scalping.config_loader import get_scalping_config
            return get_scalping_config().min_confidence
        except Exception:
            from app.config import settings
            return settings.scalping.SCALPING_MIN_CONFIDENCE

    def _are_collectors_concordi(self, market_score: SignalScore) -> tuple[bool, set[str], float]:
        """Verifica se i collector attivi sono tutti concordi (stesso bias).

        Returns:
            tuple: (sono_concordi, set_dei_bias, score_medio_attivo)
        """
        active_biases = set()
        active_scores = []
        for origin_key, origin_score in (market_score.breakdown or {}).items():
            if origin_score is not None and isinstance(origin_score, (int, float)):
                if origin_score > 0:
                    active_biases.add("bullish")
                    active_scores.append(origin_score)
                elif origin_score < 0:
                    active_biases.add("bearish")
                    active_scores.append(origin_score)
                # score == 0 è neutrale, non conta come bias

        avg_active_score = sum(active_scores) / len(active_scores) if active_scores else 0.0
        return len(active_biases) == 1, active_biases, avg_active_score

    def should_execute(
        self,
        technical: TechnicalSignal,
        market_score: SignalScore,
        symbol: str = "",
        paper_mode: bool = False,
        ta_patterns: Optional[dict] = None,
        vol_anomaly: bool = False,
    ) -> ExecutionDecision:
        """Decide se eseguire un ordine basandosi su intelligence + tecnico e volumi.

        Args:
            technical: Segnale tecnico dalla strategia attiva.
            market_score: Score intelligence dal SignalScoreEngine.
            symbol: Simbolo (per log).
            paper_mode: Se True, usa solo segnale tecnico (per debug/test).

        Returns:
            ExecutionDecision con execute=True/False e motivazione.
        """
        min_confidence = self._get_min_confidence()

        trend_str = ""
        if market_score.trend_direction:
            t_val = market_score.trend_5m or 0.0
            trend_val = f"+{t_val:.1f}" if t_val > 0 else f"{t_val:.1f}"
            trend_str = f" [trend={trend_val} {market_score.trend_direction}]"

        # Se il technical e' NONE, non fare nulla
        if technical.type == "NONE":
            return ExecutionDecision(
                execute=False,
                reason="nessun segnale tecnico",
                signal_type=technical.type,
                ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
            )

        # ── FIX-2026-06-12: CLOSE sempre permesso ──
        if technical.type == "CLOSE":
            logger.info(
                f"{GREEN}🟢 CLOSE {symbol} sempre permesso (segnale di uscita, non filtrato da bias){RESET}"
            )
            return ExecutionDecision(
                execute=True,
                confidence=min(technical.confidence, 1.0),
                reason=f"close_signal: {technical.type}@{technical.confidence:.2f} (uscita sempre permessa)",
                signal_type=technical.type,
                ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
            )

        # Conta tutti i collector che hanno risposto (non None)
        # Un collector con score 0.0 è comunque un dato valido (neutro)
        num_collectors_responded = len(market_score.breakdown) if market_score.breakdown else 0
        mode_label = "PAPER" if paper_mode else "LIVE"

        from app.scalping.config_loader import get_scalping_config
        min_collectors = get_scalping_config().min_collectors

        # ── Caso 1: POCHI COLLECTOR → bypass intelligence solo se discordi ──
        if num_collectors_responded < min_collectors:
            are_concordi, active_biases, avg_score = self._are_collectors_concordi(market_score)
            only_one_bias = len(active_biases) == 1
            bypass_reason = (
                f"score={market_score.total:.1f} "
                f"({num_collectors_responded} significant collectors, "
                f"bias={active_biases if active_biases else 'none'})"
            )

            # Se i collector attivi sono tutti concordi → NON bypassare
            if only_one_bias and abs(market_score.total) >= 5.0:
                logger.warning(
                    f"{RED}🔴 BLOCK: {symbol} |score|={market_score.signal_strength:.1f} < threshold "
                    f"(collector concordi, bypass bloccato: {bypass_reason}){RESET}"
                )
                return ExecutionDecision(
                    execute=False,
                    reason=f"collector concordi ({list(active_biases)[0]}), score={market_score.total:.1f}",
                    signal_type=technical.type,
                    ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
                )

            # Collector discordi o pochi dati → bypass intelligence (usa solo tecnico)
            if technical.confidence >= min_confidence:
                logger.info(
                    f"{YELLOW}📋 {mode_label} MODE: {technical.type} {symbol} @ {technical.confidence:.2f} "
                    f"(intelligence bypassed: {bypass_reason}){RESET}"
                )
                return ExecutionDecision(
                    execute=True,
                    confidence=technical.confidence,
                    reason=f"{mode_label.lower()}_mode fallback (no intel): {technical.type}@{technical.confidence:.2f}",
                    signal_type=technical.type,
                    ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
                )
            else:
                return ExecutionDecision(
                    execute=False,
                    reason=f"{mode_label.lower()}_mode: technical confidence {technical.confidence:.2f} < {min_confidence}",
                    signal_type=technical.type,
                    ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
                )

        # ── Caso 2: COLLECTOR SUFFICIENTI MA SCORE NEUTRALE → BLOCCO ──
        if abs(market_score.total) < 5.0:
            reason = (
                f"intelligence neutrale "
                f"({num_collectors_responded} collectors, score={market_score.total:.1f}){trend_str}"
            )
            logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
                ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
            )

        # ── Caso 3: SCORE ≥ 5.0 → filtro soglia ────────────────────────
        if not market_score.tradeable:
            from app.scalping.config_loader import get_scalping_config
            soglia = get_scalping_config().signal_strength_threshold
            # Log pulito: mostra |score| < threshold (confronto reale, nessuna ambiguità)
            reason = (
                f"|score|={market_score.signal_strength:.1f} < threshold {soglia}{trend_str}"
            )
            logger.warning(
                f"{RED}🔴 BLOCK: {symbol} {reason} (bias={market_score.bias}){RESET}"
            )
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
                ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
            )

        # ── Mean-reversion bypass per strategie ranging ─────────────────
        MEAN_REVERSION_STRATEGIES = ("rsi_bollinger", "stoch_rsi_bb_squeeze")
        bias = market_score.bias

        if bias == "bullish" and technical.type not in ("BUY",):
            if technical.type == "SELL" and technical.source and any(
                technical.source.startswith(s) for s in MEAN_REVERSION_STRATEGIES
            ):
                logger.info(
                    f"⚡ MEAN-REVERSION SELL permesso (source={technical.source}) "
                    f"nonostante bias={bias} — chiusura range, non short direzionale"
                )
            else:
                reason = f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}{trend_str}"
                logger.info(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
                return ExecutionDecision(
                    execute=False,
                    reason=reason,
                    signal_type=technical.type,
                    ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
                )

        if bias == "bearish" and technical.type not in ("SELL", "CLOSE"):
            if technical.type == "BUY" and technical.source and any(
                technical.source.startswith(s) for s in MEAN_REVERSION_STRATEGIES
            ):
                logger.info(
                    f"⚡ MEAN-REVERSION BUY permesso (source={technical.source}) "
                    f"nonostante bias={bias}{trend_str} — chiusura range, non long direzionale"
                )
            else:
                reason = f"conflitto intelligence-tecnico: bias={bias}, segnale={technical.type}{trend_str}"
                logger.info(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
                return ExecutionDecision(
                    execute=False,
                    reason=reason,
                    signal_type=technical.type,
                    ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
                )

        if bias == "neutral":
            reason = "bias intelligence neutrale, no trade"
            logger.warning(f"{YELLOW}🟡 SKIP: {symbol} {reason} (score={market_score.total:.1f}){RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
                ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
            )

        # ── Logica TA & Volume: Blocco Preventivo o Boost (per posizioni BUY) ──
        score_ta = ta_patterns.get("score", 0) if ta_patterns else 0
        if technical.type == "BUY" and vol_anomaly:
            # Se abbiamo volumi molto alti e un sentiment fortemente ribassista dai pattern
            if score_ta < -1:
                reason = f"TA FILTER BLOCK: anomalia di volume ({vol_anomaly}) con forti pattern BEARISH (score={score_ta})"
                logger.warning(f"{RED}🔴 BLOCK: {symbol} {reason}{RESET}")
                return ExecutionDecision(
                    execute=False,
                    reason=reason,
                    signal_type=technical.type,
                    ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
                )
            # Se abbiamo volumi molto alti e un sentiment rialzista dai pattern, spingiamo il confidence
            elif score_ta > 0:
                boost_amount = 0.2
                logger.info(f"🚀 TA FILTER BOOST: anomalia di volume con pattern BULLISH (score={score_ta}) -> Aggiungo +{boost_amount} al confidence")
                # Lo applichiamo temporaneamente al tecnico per il calcolo combinato
                technical = TechnicalSignal(
                    type=technical.type,
                    confidence=min(technical.confidence + boost_amount, 1.0),
                    source=technical.source
                )

        # ── Calcolo confidenza combinata (pesata 70% tecnico, 30% intelligence) ──
        # Motivazione: la confidence tecnica è più reattiva al prezzo (rsi_bollinger
        # vede subito il tocco della banda), mentre l'intelligence è un filtro più
        # lento e generico. Dare 50/50 penalizza troppo il tecnico.
        signal_norm = (market_score.signal_strength or 0.0) / 100.0  # 0..1
        combined = signal_norm * 0.3 + technical.confidence * 0.7

        if combined < min_confidence:
            reason = f"confidenza combinata {combined:.2f} < soglia {min_confidence}"
            logger.warning(f"{YELLOW}🟡 SKIP: {symbol} {reason}{RESET}")
            return ExecutionDecision(
                execute=False,
                reason=reason,
                signal_type=technical.type,
                ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
            )

        # ── TRADE ESEGUITO ───────────────────────────────────────────────
        reason_str = (
            f"intelligence={market_score.total:.1f} ({market_score.bias}){trend_str} + "
            f"tecnico={technical.type}@{technical.confidence:.2f}"
        )
        if vol_anomaly and score_ta > 0:
            reason_str += f" [BOOST TA: {score_ta} patterns]"
            
        logger.info(
            f"{GREEN}🟢 SIGNAL: {technical.type} {symbol} conf={combined:.3f} | {reason_str}{RESET}"
        )
        return ExecutionDecision(
            execute=True,
            confidence=round(combined, 3),
            reason=reason_str,
            signal_type=technical.type,
            ta_patterns=ta_patterns, vol_anomaly=vol_anomaly
        )