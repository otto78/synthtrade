"""Supervisor Client - riutilizza cascata modelli per chiamate Claude."""

import logging
from typing import Optional

from app.ai.model_client import ModelClient, AllModelsUnavailableError
from app.ai.eval_parser import parse_supervisor_decision
from app.ai.supervisor_context import build_scalping_context
from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore
from app.scalping.models.market import MarketRegime
from app.scalping.models.supervisor import SupervisorDecision
from app.config import settings

logger = logging.getLogger(__name__)

# System prompt con gerarchia segnali v2.0
_SUPERVISOR_SYSTEM_PROMPT = '''
You are an AI trading supervisor for a scalping system. Analyze the intelligence data and provide a decision.

Signal Hierarchy (priority order):
1. Funding Rate: > 0.1% = overleveraged long (short bias), < -0.1% = overleveraged short (long bias)
2. CVD: positive = buy pressure, negative = sell pressure
3. Open Interest: growing with sideways price = breakout imminent
4. Long/Short Ratio: > 70% long = overexposed, > 70% short = oversold
5. Fear & Greed: < 20 or > 80 = potential reversal
6. On-chain Exchange Flow: inflow = bearish, outflow = bullish
7. Sentiment: confirmation only
8. Technical indicators (EMA, RSI, BB): timing filters only

Respond ONLY with JSON:
```json
{
  "action": "update_params|change_strategy|pause_trading|resume_trading|no_action",
  "reason": "explanation referencing real data",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "which signal drove the decision",
  "new_params": {...} or null,
  "new_strategy": "ema_cross|rsi_bollinger|vwap_reversion" or null
}
```
'''


class SupervisorClient:
    """Client per supervisor AI che riutilizza la cascata modelli esistente."""

    def __init__(self):
        self._client = ModelClient(
            api_key=settings.ANTHROPIC_API_KEY,
            api_base_url=settings.ANTHROPIC_BASE_URL,
            cascade_models=settings.MODEL_CASCADE,
            fallback_model=settings.MODEL_FALLBACK,
        )

    async def decide(
        self,
        symbol: str,
        snapshot: Optional[MarketIntelSnapshot] = None,
        regime: Optional[MarketRegime] = None,
        score: Optional[SignalScore] = None,
    ) -> SupervisorDecision:
        """Ottieni decisione dal supervisor AI."""
        context = build_scalping_context(symbol, snapshot, regime, score)

        user_prompt = f"""Current market intelligence for {symbol}:
{self._format_context(context)}

Provide your decision:"""

        try:
            response = await self._client.call_with_fallback(
                system=_SUPERVISOR_SYSTEM_PROMPT,
                user=user_prompt,
            )
            return parse_supervisor_decision(response.content)
        except AllModelsUnavailableError as e:
            logger.error(f"All models unavailable for supervisor: {e}")
            return SupervisorDecision(
                action="no_action",
                reason="All AI models unavailable",
                confidence=0.0,
            )

    def _format_context(self, context: dict) -> str:
        """Format context dict as readable text."""
        lines = []
        if "regime" in context:
            lines.append(f"Regime: {context['regime']} (confidence: {context.get('regime_confidence', 0):.2f})")
        if "funding_rate" in context:
            fr = context["funding_rate"]
            lines.append(f"Funding Rate: {fr['rate']:.4f} ({fr['interpretation']})")
        if "cvd" in context:
            cvd = context["cvd"]
            lines.append(f"CVD: {cvd['value']:.0f} ({cvd['trend']})")
        if "open_interest" in context:
            lines.append(f"Open Interest: ${context['open_interest']:,.0f}")
        if "long_short_ratio" in context:
            lsr = context["long_short_ratio"]
            lines.append(f"Long/Short: {lsr['long_pct']:.0f}%/{lsr['short_pct']:.0f}%")
        if "fear_greed" in context:
            fg = context["fear_greed"]
            lines.append(f"Fear & Greed: {fg['value']} ({fg['label']})")
        if "signal_score" in context:
            ss = context["signal_score"]
            lines.append(f"Signal Score: {ss['total']:.1f} ({ss['bias']})")
        return "\n".join(lines)