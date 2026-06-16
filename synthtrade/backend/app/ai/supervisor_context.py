"""Supervisor Context Builder - estende context per scalping intelligence."""

from typing import Optional
from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore
from app.scalping.models.market import MarketRegime


def build_scalping_context(
    symbol: str,
    snapshot: Optional[MarketIntelSnapshot],
    regime: Optional[MarketRegime],
    score: Optional[SignalScore],
) -> dict:
    """Costruisce il context per il supervisor AI.

    Include la gerarchia segnali v2.0 per la decisione.
    """
    context = {
        "symbol": symbol,
        "regime": regime.regime if regime else "unknown",
        "regime_confidence": regime.confidence if regime else 0.0,
    }

    # Threshold corrente (può essere modificato dal Supervisor stesso)
    from app.scalping.config_loader import get_scalping_config
    context["current_threshold"] = get_scalping_config().signal_strength_threshold

    if snapshot:
        # Funding Rate
        if snapshot.funding_rate:
            fr = snapshot.funding_rate
            context["funding_rate"] = {
                "rate": float(fr.rate),
                "interpretation": _interpret_funding(float(fr.rate)),
            }

        # CVD
        if snapshot.cvd:
            context["cvd"] = {
                "value": float(snapshot.cvd.cvd),
                "trend": snapshot.cvd.trend,
            }

        # Open Interest
        if snapshot.open_interest:
            context["open_interest"] = float(snapshot.open_interest.value_usd)

        # Long/Short Ratio
        if snapshot.long_short_ratio:
            context["long_short_ratio"] = {
                "long_pct": float(snapshot.long_short_ratio.long_pct),
                "short_pct": float(snapshot.long_short_ratio.short_pct),
            }

        # Fear & Greed
        if snapshot.fear_greed:
            context["fear_greed"] = {
                "value": snapshot.fear_greed.value,
                "label": snapshot.fear_greed.label,
            }

    if score:
        context["signal_score"] = {
            "total": score.total,
            "bias": score.bias,
            "tradeable": score.tradeable,
            "breakdown": score.breakdown,
        }

        # Calcola gap per passare il gate
        abs_score = abs(score.total)
        threshold = context["current_threshold"]
        gap = threshold - abs_score
        context["threshold_gap"] = round(gap, 1)

    # Collector attivi e assenti — letti dal breakdown dello score (quali collector hanno risposto)
    if score and score.breakdown:
        active_collectors = list(score.breakdown.keys())
        all_possible = ["funding_rate", "cvd", "open_interest", "long_short_ratio", "fear_greed", "sentiment", "whale"]
        missing = [c for c in all_possible if c not in active_collectors]
        context["active_collectors"] = active_collectors
        context["missing_collectors"] = missing

    return context


def _interpret_funding(rate: float) -> str:
    """Interpreta funding rate."""
    if rate > 0.001:  # 0.1%
        return "overleveraged_long"
    elif rate < -0.001:
        return "overleveraged_short"
    return "neutral"