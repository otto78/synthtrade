"""Supervisor Client - riutilizza cascata modelli per chiamate Claude."""

import logging
from typing import Optional

from app.ai.model_client import AllModelsUnavailableError
from app.ai.eval_parser import parse_supervisor_decision
from app.ai.supervisor_context import build_scalping_context
from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore
from app.scalping.models.market import MarketRegime
from app.scalping.models.supervisor import SupervisorDecision
from app.services.llm_model_service import LLMModelService

logger = logging.getLogger(__name__)

# System prompt con gerarchia segnali v2.0
_SUPERVISOR_SYSTEM_PROMPT = '''
Sei un supervisore AI esperto in trading scalping. Analizza i dati di intelligence forniti e prendi una decisione operativa.

Gerarchia dei Segnali (ordine di priorità):
1. Funding Rate: > 0.1% = leva eccessiva long (bias short), < -0.1% = leva eccessiva short (bias long)
2. CVD: positivo = pressione acquisto, negativo = pressione vendita
3. Open Interest: in crescita con prezzo laterale = breakout imminente
4. Long/Short Ratio: > 70% long = sovraesposizione, > 70% short = oversold
5. Fear & Greed: < 20 o > 80 = potenziale inversione
6. Flusso Exchange On-chain: inflow = bearish, outflow = bullish
7. Sentiment: solo per conferma
8. Indicatori Tecnici (EMA, RSI, BB): solo come filtri di timing

IMPORTANTE: Rispondi SEMPRE in lingua ITALIANA nel campo "reason".

Rispondi SOLO con un oggetto JSON valido:
```json
{
  "action": "update_params|change_strategy|pause_trading|resume_trading|no_action",
  "reason": "spiegazione dettagliata in italiano facendo riferimento ai dati reali",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "quale segnale ha guidato la decisione",
  "new_params": {...} or null,
  "new_strategy": "ema_cross|rsi_bollinger|vwap_reversion" or null
}
```
'''


class SupervisorClient:
    """Client per supervisor AI che riutilizza la cascata modelli esistente."""

    def __init__(self):
        """Create supervisor client using models from DB (or settings fallback)."""
        service = LLMModelService()
        self._client = service.create_model_client()

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