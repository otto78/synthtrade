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

# System prompt con gerarchia segnali v2.0 + update_threshold
_SUPERVISOR_SYSTEM_PROMPT = '''
Sei un supervisore AI esperto in trading scalping. Analizza i dati di intelligence forniti e prendi una decisione operativa.

⚠️ REGOLA CRITICA — mapping regime/strategia obbligatorio:
- regime=ranging  → puoi scegliere SOLO: rsi_bollinger, momentum_base, stoch_rsi_bb_squeeze
- regime=trending_up o trending_down → puoi scegliere SOLO: ema_cross
- regime=volatile → puoi scegliere SOLO: stoch_rsi_bb_squeeze, momentum_base
- regime=unknown → puoi scegliere SOLO: momentum_base
- Non puoi MAI assegnare ema_cross a un mercato ranging, indipendentemente dal bias.
  Il bias bullish in ranging si sfrutta con mean-reversion (rsi_bollinger), non trend-following.
- Non puoi MAI assegnare stoch_rsi_bb_squeeze in trending perché sprecherebbe breakout reali.

⚠️ AZIONE update_threshold — modifica la soglia di signal strength:
- Il contesto mostra la soglia corrente (Current Signal Strength Threshold)
  con score attuale, gap per passare il gate, collector attivi/assenti, coverage
- Se lo score intelligence è sempre sotto soglia ma il segnale tecnico è forte e ripetuto,
  e la copertura collector è buona (coverage > 70%), valuta di ABBASSARE la soglia
  per permettere trade. Nuova soglia consigliata: ~10.0
- Se ci sono molti falsi segnali (trade in perdita nonostante score sopra soglia),
  valuta di ALZARE la soglia per maggiore selettività. Nuova soglia consigliata: ~18.0
- Se il coverage è basso (< 60%), NON abbassare la soglia perché score inaffidabile
- Se lo score è stabile tra -5 e +5 per più di 10 candele e il regime è ranging,
  abbassa threshold a 8-10 per evitare blocchi prolungati
- Se ci sono stati trade con perdita consecutiva, alza threshold di 2-3 punti
  per maggiore protezione
- Non modificare threshold più di una volta ogni 30 minuti (cooldown automatico)
- La soglia non può scendere sotto 5.0 né salire sopra 30.0 (limiti di sicurezza)
- Usa update_threshold come alternativa conservativa prima di change_strategy:
  se la strategia sembra giusta ma non passa il filtro intelligence, abbassa la soglia
  invece di cambiare strategia
- Per update_threshold, passa nel campo new_params il valore:
  {"signal_strength_threshold": NUOVO_VALORE}

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
  "action": "update_params|change_strategy|update_threshold|pause_trading|resume_trading|no_action",
  "reason": "spiegazione dettagliata in italiano facendo riferimento ai dati reali",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "quale segnale ha guidato la decisione",
  "new_params": {...} or null (per update_threshold: {"signal_strength_threshold": 10.0}),
  "new_strategy": "ema_cross|rsi_bollinger|stoch_rsi_bb_squeeze|momentum_base|vwap_reversion" or null
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
        
        # === CONFIGURAZIONE INTELLIGENCE ===
        threshold = context.get("current_threshold", 15.0)
        lines.append("")
        lines.append("=== CONFIGURAZIONE INTELLIGENCE ===")
        lines.append(f"Soglia score minima (threshold): {threshold}")
        
        ss = context.get("signal_score")
        if ss:
            abs_score = abs(ss["total"])
            gap = context.get("threshold_gap", threshold - abs_score)
            lines.append(f"Score attuale: {ss['total']:.1f} (|score|={abs_score:.1f})")
            lines.append(f"Gap per passare il gate: {gap:+.1f} punti")
            lines.append(f"Bias: {ss['bias']}")
            
            # Collector attivi/assenti
            active = context.get("active_collectors", [])
            missing = context.get("missing_collectors", [])
            total = len(active) + len(missing)
            lines.append(f"Collector attivi: {len(active)}/{total} ({', '.join(active)})")
            if missing:
                lines.append(f"Collector assenti: {', '.join(missing)}")
            
            # Coverage (calcolato approssimativamente)
            if total > 0:
                coverage = len(active) / total
                lines.append(f"Coverage: {coverage:.0%}")
                if coverage < 0.6:
                    lines.append("⚠️ Coverage < 60% — dati inaffidabili, NON abbassare la soglia!")
                elif coverage >= 0.7:
                    lines.append("✅ Coverage buono — modifiche soglia consentite")
            
            lines.append(f"Nota: lo score deve superare la threshold ({threshold}) in valore assoluto E avere bias non neutral.")
        
        lines.append("")
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
        if ss:
            lines.append(f"Signal Score: {ss['total']:.1f} ({ss['bias']})")
        return "\n".join(lines)
