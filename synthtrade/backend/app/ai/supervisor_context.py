"""Supervisor Context Builder - estende context per scalping intelligence."""

import asyncio
from typing import Optional
from app.scalping.models.intelligence import MarketIntelSnapshot, SignalScore
from app.scalping.models.market import MarketRegime


async def build_scalping_context(
    symbol: str,
    snapshot: Optional[MarketIntelSnapshot],
    regime: Optional[MarketRegime],
    score: Optional[SignalScore],
    session_id: Optional[str] = None,
    trade_history: Optional[list] = None,  # TASK-860: performance sessione in-memory
) -> dict:
    """Costruisce il context per il supervisor AI.

    Include la gerarchia segnali v2.0 per la decisione,
    la configurazione intelligence corrente,
    la performance della sessione attuale,
    e la storia delle ultime decisioni del supervisor.

    Args:
        symbol: Simbolo trading (es: BNBUSDC)
        snapshot: Snapshot intelligence corrente
        regime: Regime di mercato corrente
        score: Score intelligence calcolato
        session_id: ID sessione DB per query performance e memoria
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

    # Collector attivi e assenti — letti dal breakdown dello score
    if score and score.breakdown:
        active_collectors = list(score.breakdown.keys())
        all_possible = ["funding_rate", "cvd", "open_interest", "long_short_ratio", "fear_greed", "sentiment", "whale"]
        missing = [c for c in all_possible if c not in active_collectors]
        context["active_collectors"] = active_collectors
        context["missing_collectors"] = missing

    # ── Performance sessione (TASK-860): prima prova trade_history in-memory, poi DB ──
    # trade_history passata direttamente dallo scheduler (più fresca, evita query DB)
    if trade_history:
        closed = [t for t in trade_history if t.get("exit_price")]
        total = len(closed)
        if total > 0:
            wins = len([t for t in closed if (t.get("pnl") or 0) > 0])
            total_pnl = sum((t.get("pnl") or 0) for t in closed)
            win_rate = wins / total * 100
            last_5 = sorted(closed, key=lambda t: t.get("timestamp", ""), reverse=True)[:5]
            context["session_performance"] = {
                "total_trades": total,
                "winning_trades": wins,
                "losing_trades": total - wins,
                "win_rate_pct": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl_per_trade": round(total_pnl / total, 2),
                "last_5_pnl": [t.get("pnl") or 0 for t in last_5],
                "last_5_reasons": [t.get("signal_reason") or "unknown" for t in last_5],
            }

    # ── Performance sessione (TASK-844) ─────────────────────────────────
    if session_id:
        try:
            from app.db.supabase_client import get_supabase

            def _fetch_session_perf():
                supabase = get_supabase()
                resp = supabase.table("scalping_trades") \
                    .select("*") \
                    .eq("session_id", session_id) \
                    .eq("status", "closed") \
                    .order("exit_time", desc=True) \
                    .limit(20) \
                    .execute()
                return resp.data if resp.data else []

            trades = await asyncio.to_thread(_fetch_session_perf)
        except Exception:
            trades = []

        if trades:
            total = len(trades)
            wins = [t for t in trades if (t.get("pnl") or 0) > 0]
            losses = [t for t in trades if (t.get("pnl") or 0) < 0]
            total_pnl = sum((t.get("pnl") or 0) for t in trades)
            win_count = len(wins)
            lose_count = len(losses)
            win_rate = win_count / total * 100 if total > 0 else 0
            last_5 = trades[:5]
            last_5_pnl = [t.get("pnl") or 0 for t in last_5]
            last_5_reasons = [t.get("signal_reason") or "unknown" for t in last_5]

            context["session_performance"] = {
                "total_trades": total,
                "winning_trades": win_count,
                "losing_trades": lose_count,
                "win_rate_pct": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl_per_trade": round(total_pnl / total, 2) if total > 0 else 0,
                "last_5_pnl": last_5_pnl,
                "last_5_reasons": last_5_reasons,
            }

    # ── Supervisor history (TASK-847) ────────────────────────────────────
    if session_id:
        try:
            from app.db.supabase_client import get_supabase

            def _fetch_supervisor_history():
                supabase = get_supabase()
                resp = supabase.table("supervisor_memory") \
                    .select("action, reason, decided_at, was_applied, market_bias") \
                    .eq("symbol", symbol) \
                    .order("decided_at", desc=True) \
                    .limit(10) \
                    .execute()
                return resp.data if resp.data else []

            history = await asyncio.to_thread(_fetch_supervisor_history)
        except Exception:
            history = []

        if history:
            history_lines = []
            for h in history:
                applied = "✅" if h.get("was_applied") else "❌"
                action = h.get("action", "?")
                reason = (h.get("reason") or "")[:60]
                decided = (h.get("decided_at") or "")[:16] if h.get("decided_at") else "?"
                history_lines.append(f"  {applied} [{decided}] {action}: {reason}")
            context["supervisor_history"] = "\n".join(history_lines)

    return context


def _interpret_funding(rate: float) -> str:
    """Interpreta funding rate."""
    if rate > 0.001:  # 0.1%
        return "overleveraged_long"
    elif rate < -0.001:
        return "overleveraged_short"
    return "neutral"