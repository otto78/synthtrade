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

# System prompt con gerarchia segnali v2.0 + update_threshold + regole NON AGIRE (TASK-861)
_SUPERVISOR_SYSTEM_PROMPT = '''
Sei un supervisore AI esperto in trading scalping. Analizza i dati di intelligence forniti e prendi una decisione operativa.

⚠️ REGOLA QUANDO NON AGIRE (rispetta SEMPRE queste regole prima di ogni altra):
- Se session_performance mostra < 5 trade totali → rispondi SEMPRE no_action
  (troppo presto per valutare la strategia, non hai dati sufficienti)
- Se le ultime 3+ decisioni nella history mostrano la stessa action che stai per proporre → rispondi SEMPRE no_action
  (loop di decisioni inutili, la misura non ha effetto)
- Se session_performance mostra win_rate > 60% e total_pnl > 0 → rispondi SEMPRE no_action
  (la strategia sta funzionando, non interferire)
- Se coverage collector < 50% → rispondi SEMPRE no_action
  (dati intelligence insufficienti per decisioni affidabili)
- Se score è nel range [-5, +5] → rispondi no_action o update_threshold al massimo
  (segnale troppo debole per cambiare strategia)

⚠️ REGOLA CRITICA — mapping regime/strategia obbligatorio:
- regime=ranging  → puoi scegliere SOLO: rsi_bollinger, momentum_base, stoch_rsi_bb_squeeze
- regime=trending_up o trending_down → puoi scegliere SOLO: ema_cross
- regime=volatile → puoi scegliere SOLO: stoch_rsi_bb_squeeze, momentum_base
- regime=unknown → puoi scegliere SOLO: momentum_base
- Non puoi MAI assegnare ema_cross a un mercato ranging, indipendentemente dal bias.
- Non puoi MAI assegnare stoch_rsi_bb_squeeze in trending perché sprecherebbe breakout reali.

⚠️ AZIONE update_threshold — modifica la soglia di signal strength:
- Se lo score è sempre sotto soglia ma segnale tecnico forte e coverage > 70% → abbassa (~10.0)
- Se molti falsi segnali (trade in perdita nonostante score sopra soglia) → alza (~18.0)
- Se coverage < 60% → NON abbassare la soglia (score inaffidabile)
- Se score stabile tra -5 e +5 per 10+ candele in ranging → abbassa a 8-10
- Se trade in perdita consecutiva → alza di 2-3 punti
- Cooldown automatico 30 minuti tra modifiche. Limiti: min 5.0, max 30.0.
- Per update_threshold: new_params = {"signal_strength_threshold": NUOVO_VALORE}

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
        session_id: Optional[str] = None,
        trade_history: Optional[list] = None,  # TASK-860
    ) -> SupervisorDecision:
        """Ottieni decisione dal supervisor AI."""
        context = await build_scalping_context(
            symbol, snapshot, regime, score,
            session_id=session_id,
            trade_history=trade_history,
        )

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

        # === PERFORMANCE SESSIONE (TASK-860) ===
        perf = context.get("session_performance")
        if perf:
            lines.append("")
            lines.append("=== PERFORMANCE SESSIONE ===")
            lines.append(
                f"Trade totali: {perf['total_trades']} | "
                f"Win rate: {perf['win_rate_pct']}% | "
                f"PnL totale: {perf['total_pnl']:.2f}"
            )
            last5 = perf.get("last_5_pnl", [])
            last5r = perf.get("last_5_reasons", [])
            if last5:
                parts = [f"{p:.2f} ({r})" for p, r in zip(last5, last5r)]
                lines.append(f"Ultimi 5: {', '.join(parts)}")
        else:
            lines.append("")
            lines.append("=== PERFORMANCE SESSIONE ===")
            lines.append("Nessun trade ancora in questa sessione.")

        # === DECISIONI PRECEDENTI (TASK-862) ===
        history = context.get("supervisor_history")
        if history:
            lines.append("")
            lines.append("=== DECISIONI PRECEDENTI (ultime 10) ===")
            lines.append(history)

        return "\n".join(lines)
