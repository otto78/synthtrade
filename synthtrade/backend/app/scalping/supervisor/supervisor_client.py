"""Supervisor Client - riutilizza cascata modelli per chiamate Claude."""

import asyncio
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

# System prompt v3 (2026-09-29): fee-aware con formula breakeven, memoria cross-sessione, anti-loop pause.
# Base di riferimento: docs/supervisor-system-prompt.md — modificare da lì e ricopiare qui.
_SUPERVISOR_SYSTEM_PROMPT = '''
Sei un supervisore AI per un sistema di scalping algoritmico. Ricevi dati di intelligence di mercato sul simbolo corrente e devi prendere una decisione operativa.
Il simbolo negoziato, l'exchange e le fee reali sono communicate a runtime nel contesto — non assumere valori fissi.

⚠️ REGOLA FEE E BREAKEVEN (valutala PRIMA della performance storica):
Nel contesto trovi il blocco === FEE REALI === con i valori esatti per questa sessione:
  - fee taker per lato (es. 0.10%)
  - fee round-trip totale = fee_in + fee_out
Formula breakeven WR = avg_loss_netto / (avg_win_netto + avg_loss_netto)
  dove avg_win_netto e avg_loss_netto sono NETTI (già dopo le fee, visibili in PERFORMANCE STORICA).
Se PERFORMANCE STORICA non ha ancora avg_win/avg_loss su questa combo, stima:
  avg_loss_lordo ≈ SL_pct + round_trip_fee,  avg_win_lordo ≈ TP_pct - round_trip_fee
Regole derivate:
- Se WR storico della combo < (breakeven WR - 5pp) con n >= 20 trade → combo strutturalmente perdente, considera change_strategy
- Se non esiste alternativa compatibile con la whitelist → no_action (non si può fare meglio con le strategie disponibili)
- NON abbassare la soglia per fare più trade se WR storico < breakeven: più trade = più perdite

⚠️ REGOLA SESSIONE APPENA AVVIATA (stop&go):
- Se PERFORMANCE SESSIONE riporta "Sessione appena avviata" con trade storici cross-sessione >= 20:
  → NON applicare la regola "troppo presto per valutare"
  → Usa la PERFORMANCE STORICA come base per decidere strategy e threshold
  → Se mismatch whitelist regime/strategia E trade storici >= 20 → change_strategy subito
  → Se WR combo storica < 35% con n >= 20 trade → change_strategy se esiste alternativa
- Se trade storici cross-sessione < 20 → applica no_action (dati davvero insufficienti)

⚠️ ORDINE DI VALUTAZIONE DELLE REGOLE (rispettalo SEMPRE):
1) REGOLA QUANDO NON AGIRE (con eccezione stop&go sopra)
2) REGOLA FEE E BREAKEVEN
3) REGOLA PERFORMANCE STORICA
4) tutto il resto (mapping strategia, threshold, anomalie)
Se una regola si applica, fermati lì.

⚠️ STRATEGIE DISPONIBILI (sono SOLO 3):
- ema_cross        → trend-following su incroci EMA, per mercati direzionali (trending_up)
- rsi_bollinger    → mean-reversion su RSI + Bollinger, per mercati laterali (ranging/trending_down)
- vwap_reversion   → reversion al VWAP, per mercati volatili o regime incerto (volatile/unknown)

⚠️ REGOLA CRITICA — mapping regime/strategia obbligatorio (whitelist):
- regime=ranging       → SOLO: rsi_bollinger
- regime=trending_up   → SOLO: ema_cross
- regime=trending_down → SOLO: rsi_bollinger
- regime=volatile      → SOLO: vwap_reversion
- regime=unknown       → SOLO: vwap_reversion
- Se la strategia attiva non è nella whitelist del regime corrente E i trade storici >= 20 → change_strategy subito
- Non puoi MAI assegnare ema_cross a ranging, né vwap_reversion a un mercato in trend.

⚠️ REGOLA QUANDO NON AGIRE (vedi eccezione stop&go sopra):
- Se session_performance mostra < 5 trade totali E i trade storici cross-sessione < 20 E NON c'è anomalia di volume → no_action
- Se le ultime 3+ decisioni nella history mostrano la stessa action che stai per proporre → no_action. ECCEZIONE: resume_trading con new_strategy diversa dalla strategia attiva.
- Se session_performance mostra win_rate > 60% e total_pnl > 0 → no_action (la strategia funziona)
- Se coverage collector < 50% → no_action (dati insufficienti)
- Se score nel range [-5, +5] → no_action o update_threshold al massimo
- resume_trading è permesso SOLO se: (a) proponi new_strategy diversa e compatibile con la whitelist, OPPURE (b) il regime è cambiato rispetto a quando è scattata la pausa.

⚠️ REGOLA ANTI-LOOP PAUSE:
- Non proporre pause_trading se è già stato applicato nelle ultime 30 minuti (controlla la history)
- Non alternare ripetutamente pause_trading e update_threshold sugli stessi dati invariati
- Se hai già pausato nelle ultime 3 decisioni applicate → no_action o resume_trading con cambio strategia

⚠️ REGOLA PERFORMANCE STORICA:
- Se PERFORMANCE STORICA mostra win_rate < 35% per la combo (regime, strategia) corrente con n_trades >= 10 → considera fortemente change_strategy
- Se PERFORMANCE STORICA mostra win_rate > 70% per la combo (regime, strategia) corrente con n_trades >= 10 → evita change_strategy
- Conta le exit da break-even/trailing come VINCITE quando interpreti i dati storici.

⚠️ TRAILING STOP & BREAK-EVEN — NON confonderli con uno stop-loss classico:
- Break-even: al raggiungimento di un profitto netto soglia, lo SL si sposta a break-even.
- Trailing stop: per ogni ulteriore profitto netto guadagnato, lo SL avanza dietro il prezzo.
- Un'exit da break-even o trailing stop è un PROFITTO BLOCCATO (mini-TP progressivo), NON una perdita.
- Se molti trade chiudono via break-even/trailing → win rate alto + avg_pnl piccolo è comportamento SANO.

⚠️ AZIONE update_threshold — modifica la soglia di signal strength:
- Se ci sono volumi anomali e/o forti pattern candlestick → abbassa la soglia (minimo 5.0)
- Se lo score è sempre sotto soglia ma segnale tecnico forte e coverage > 70% → abbassa (~10.0)
- Se molti falsi segnali (trade in perdita nonostante score sopra soglia) → alza (~18.0)
- Se WR storico < breakeven → NON abbassare la soglia (più trade = più perdite)
- Cooldown automatico 30 minuti tra modifiche. Limiti: min 5.0, max 30.0.
- Per update_threshold: new_params = {"signal_strength_threshold": NUOVO_VALORE}

⚠️ AZIONE update_params — quando usarla:
- Usala SOLO se hai un parametro strategico specifico da cambiare.
- Per la soglia dello score usa SEMPRE update_threshold, MAI update_params.

⚠️ PARAMETRI MODIFICABILI PER STRATEGIA:
- ema_cross:      { "min_slope": 0.0003 }
- rsi_bollinger:  { "atr_thresholds": [...], "rsi_oversold": [...], "rsi_overbought": [...], "bb_tolerance": [...], "confidence": [...] }
- vwap_reversion: { "vwap_distance_buy": 0.002, "vwap_lookback": 20 }

Gerarchia dei Segnali (ordine di priorità):
1. Funding Rate: > 0.1% = leva eccessiva long (bias short), < -0.1% = leva eccessiva short (bias long)
2. CVD: positivo = pressione acquisto, negativo = pressione vendita
3. Open Interest: in crescita con prezzo laterale = breakout imminente
4. Long/Short Ratio: > 70% long = sovraesposizione, > 70% short = oversold
5. Fear & Greed: < 20 o > 80 = potenziale inversione
6. Flusso Exchange On-chain: inflow = bearish, outflow = bullish
7. Sentiment: solo per conferma
8. Indicatori Tecnici: solo come filtri di timing

ECCEZIONE: se Anomalia di Volume = SÌ, il segnale tecnico può avere priorità per update_threshold (abbassare soglia per breakout).

NOTA: le posizioni SHORT non sono ancora supportate, i segnali SELL per apertura vengono sempre bloccati.

IMPORTANTE: Rispondi SEMPRE in lingua ITALIANA nel campo "reason".

Rispondi SOLO con un oggetto JSON valido:
{
  "action": "update_params|change_strategy|update_threshold|pause_trading|resume_trading|no_action",
  "reason": "spiegazione dettagliata in italiano facendo riferimento ai dati reali del contesto, incluso il calcolo esplicito del breakeven WR",
  "confidence": 0.0-1.0,
  "market_bias": "bullish|bearish|neutral",
  "primary_signal": "quale segnale ha guidato la decisione",
  "new_params": {...} or null,
  "new_strategy": "ema_cross|rsi_bollinger|vwap_reversion" or null
}

REGOLE SUI CAMPI JSON:
- confidence: 0.3-0.5 se solo 1-2 segnali forti, 0.6-0.8 se 3+ concordanti, 0.9+ solo con coverage > 80%.
- new_strategy: valorizzato SOLO per action=change_strategy o resume_trading con cambio strategia. Altrimenti DEVE essere null.
'''


class SupervisorClient:
    """Client per supervisor AI che riutilizza la cascata modelli esistente."""

    def __init__(self):
        """Create supervisor client using dedicated cascade for critical decisions."""
        service = LLMModelService()
        self._client = service.create_model_client(use_case="supervisor")

    async def decide(
        self,
        symbol: str,
        snapshot: Optional[MarketIntelSnapshot] = None,
        regime: Optional[MarketRegime] = None,
        score: Optional[SignalScore] = None,
        session_id: Optional[str] = None,
        trade_history: Optional[list] = None,  # TASK-860
        ta_patterns: Optional[dict] = None,
        vol_anomaly: bool = False,
        strategy_name: Optional[str] = None,  # TASK-1249: strategia attiva
        strategy_params: Optional[dict] = None,  # TASK-1249: parametri strategia attiva
        hold_return_pct: Optional[float] = None,  # Confronto vs buy-and-hold
    ) -> SupervisorDecision:
        """Ottieni decisione dal supervisor AI.

        TASK-909: Run AI call in separate thread pool to avoid blocking APScheduler event loop.
        TASK-1249: strategy_name/strategy_params esposti nel context per permettere
        all'AI di usare update_params in modo mirato.
        """
        context = await build_scalping_context(
            symbol, snapshot, regime, score,
            session_id=session_id,
            trade_history=trade_history,
            ta_patterns=ta_patterns,
            vol_anomaly=vol_anomaly,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            hold_return_pct=hold_return_pct,
        )

        user_prompt = f"""Current market intelligence for {symbol}:
{self._format_context(context)}

Provide your decision:"""

        try:
            # TASK-909: Run the async AI call in a thread pool to avoid blocking the main event loop
            # This allows APScheduler to continue processing other jobs during the AI call
            def _sync_ai_wrapper():
                """Sync wrapper that runs the async AI call in its own event loop."""
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._client.call_with_fallback(
                        system=_SUPERVISOR_SYSTEM_PROMPT,
                        user=user_prompt,
                    ))
                finally:
                    loop.close()

            response = await asyncio.to_thread(_sync_ai_wrapper)
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

        # === FEE AWARENESS (TASK-1261) ===
        fee_info = context.get("fee_info")
        if fee_info:
            taker = fee_info.get("taker_pct", 0.10)
            drag = fee_info.get("round_trip_drag_pct", 0.1999)
            lines.append("")
            lines.append("=== FEE REALI ===")
            lines.append(f"Fee taker: {taker:.4f}% per lato | Round-trip drag: {drag:.4f}%")
            lines.append(
                f"Formula breakeven WR = avg_loss_netto / (avg_win_netto + avg_loss_netto). "
                f"Stima con SL/TP da PERFORMANCE STORICA o parametri sessione."
            )
        
        # === STRATEGIA ATTIVA & PARAMETRI (TASK-1249) ===
        strategy_name = context.get("strategy_name")
        if strategy_name:
            lines.append("")
            lines.append("=== STRATEGIA ATTIVA ===")
            lines.append(f"Strategia corrente: {strategy_name}")
            params = context.get("strategy_params")
            if params:
                lines.append("Parametri correnti (modificabili via update_params):")
                for k, v in params.items():
                    lines.append(f"  - {k}: {v}")
            else:
                lines.append("Parametri: nessuno esposto")

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

        # === ANALISI TECNICA & VOLUMI ===
        lines.append("")
        lines.append("=== ANALISI TECNICA & VOLUMI ===")
        if context.get("ta_patterns"):
            score_ta = context["ta_patterns"].get("score", 0)
            bullish = len(context["ta_patterns"].get("bullish", []))
            bearish = len(context["ta_patterns"].get("bearish", []))
            lines.append(f"Pattern Candlestick: Score = {score_ta} ({bullish} bullish, {bearish} bearish)")
        else:
            lines.append("Pattern Candlestick: Nessuno")
            
        anomaly = "SÌ (Volumi eccezionalmente alti!)" if context.get("vol_anomaly") else "No"
        lines.append(f"Anomalia di Volume: {anomaly}")

        # === PERFORMANCE SESSIONE (TASK-860) ===
        perf = context.get("session_performance")
        if perf:
            lines.append("")
            lines.append("=== PERFORMANCE SESSIONE ===")
            session_just_started = perf.get("session_just_started", False)
            if session_just_started:
                # TASK-1261: sessione appena partita (stop&go), ma lo storico cross-sessione esiste
                hist_perf = context.get("historical_performance", {})
                hist_total = hist_perf.get("total_historical_trades", 0) if hist_perf else 0
                lines.append(
                    f"Sessione appena avviata (stop&go): 0 trade in questa sessione. "
                    f"Lo storico cross-sessione ha {hist_total} trade — usa PERFORMANCE STORICA per decidere. "
                    f"Non applicare la regola 'troppo presto' se i trade storici sono >= 20."
                )
            else:
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

        # === DECISIONI PRECEDENTI (TASK-862) ===
        history = context.get("supervisor_history")
        if history:
            lines.append("")
            lines.append("=== DECISIONI PRECEDENTI (ultime 10) ===")
            lines.append(history)

        # === PERFORMANCE STORICA (TASK-901/902) ===
        hist_perf = context.get("historical_performance")
        if hist_perf and hist_perf.get("total_historical_trades", 0) > 0:
            lines.append("")
            lines.append("=== PERFORMANCE STORICA (tutte le sessioni) ===")
            
            perf_data = hist_perf.get("historical_performance", {})
            insufficient = []
            
            for combo, data in perf_data.items():
                if data.get("insufficient_data"):
                    insufficient.append(combo)
                else:
                    n_trades = data.get("n_trades", 0)
                    win_rate = data.get("win_rate_pct", 0.0)
                    avg_pnl = data.get("avg_pnl", 0.0)
                    lines.append(f"{combo}: {n_trades} trade | win_rate={win_rate:.1f}% | avg_pnl={avg_pnl:.2f} USDC")
            
            if insufficient:
                lines.append(f"[campione insufficiente: {', '.join(insufficient)}]")
            
            best = hist_perf.get("best_combination")
            worst = hist_perf.get("worst_combination")
            if best and worst:
                lines.append(f"Migliore: {best} | Peggiore: {worst}")
            
            total = hist_perf.get("total_historical_trades", 0)
            lines.append(f"Totale trade storici: {total}")

        return "\n".join(lines)
