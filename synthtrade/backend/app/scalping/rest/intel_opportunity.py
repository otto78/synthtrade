import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.scalping._state import _execution_state
from app.scalping.broadcast import _now
from app.scalping.pricing import _is_valid_uuid
from app.db.supabase_client import get_supabase
from app.scalping.models.opportunity import OpportunityCategory, OpportunityUrgency
from app.scalping.opportunity.scheduler import OpportunityScheduler
from app.scalping.rest.market_data import _snapshot_to_dict

logger = logging.getLogger(__name__)

router = APIRouter()

# Opportunity scheduler singleton
_opportunity_scheduler: Optional[OpportunityScheduler] = None


async def _get_opportunity_scheduler() -> OpportunityScheduler:
    """Lazy init dello scheduler opportunity."""
    global _opportunity_scheduler
    if _opportunity_scheduler is None:
        _opportunity_scheduler = OpportunityScheduler()
        await _opportunity_scheduler.start(interval=60)
    return _opportunity_scheduler


@router.get("/intelligence/{symbol}/snapshot")
async def get_intel_snapshot(symbol: str) -> Dict:
    """Get latest market intelligence snapshot for symbol."""
    engine = _execution_state.get("signal_engine")
    
    if engine and engine.symbol == symbol:
        try:
            snapshot = await engine.get_snapshot()
            return _snapshot_to_dict(symbol, snapshot)
        except Exception:
            logger.warning(f"SignalScoreEngine failed for {symbol}, using fallback")
    
    active_symbol = _execution_state.get("session", {}).get("symbol")
    if active_symbol and symbol.upper() != active_symbol.upper():
        logger.debug(f"Intel snapshot: {symbol} != active {active_symbol}, returning empty")
        return {
            "symbol": symbol,
            "funding_rate": 0.0,
            "open_interest": 0,
            "long_pct": 0,
            "short_pct": 0,
            "cvd_trend": "neutral",
            "fear_greed_value": 50,
            "fear_greed_label": "Neutral",
            "signal_score": 50.0,
            "signal_bias": "neutral",
            "tradeable": False,
            "breakdown": {},
            "recorded_at": _now(),
        }
    
    return {
        "symbol": symbol,
        "funding_rate": 0.0,
        "open_interest": 0,
        "long_pct": 0,
        "short_pct": 0,
        "cvd_trend": "neutral",
        "fear_greed_value": 50,
        "fear_greed_label": "Neutral",
        "signal_score": 50.0,
        "signal_bias": "neutral",
        "tradeable": False,
        "breakdown": {},
        "recorded_at": _now(),
    }


@router.get("/intelligence/{symbol}/history")
async def get_intel_history(symbol: str, limit: int = 100) -> List[Dict]:
    """Get historical intelligence snapshots from Supabase."""
    try:
        supabase = get_supabase()
        response = supabase.table("market_intel_snapshots") \
            .select("*") \
            .eq("symbol", symbol) \
            .order("recorded_at", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        logger.warning(f"Failed to fetch intel history from DB: {e}")
        return []


@router.get("/debug/session-load")
async def debug_session_load():
    guard = _execution_state.get("session_load_guard")
    if not guard:
        return {"state": "no_guard"}
    return guard.monitor_data


@router.get("/debug/pipeline")
async def debug_pipeline():
    """Diagnostic endpoint to inspect pipeline state."""
    loop = _execution_state.get("loop")
    buffer_info = {"size": 0, "ready": False, "latest": None}
    if loop and hasattr(loop, "_candle_buffer"):
        buf = loop._candle_buffer
        buffer_info = {
            "buffer_id": id(buf),
            "size": len(buf),
            "ready": buf.is_ready(),
            "latest_candle": {
                "close": float(buf.latest.close),
                "timestamp": str(buf.latest.timestamp),
            } if buf.latest else None,
        }

    strategy_name = loop.strategy.name if loop and loop.strategy else None
    regime_name = loop.regime.regime if loop and loop.regime else None

    ws_client = _execution_state.get("ws_client")
    ws_connected = ws_client is not None and not ws_client._stop_event.is_set() if ws_client else False

    return {
        "buffer": buffer_info,
        "execution_loop": {
            "strategy": strategy_name,
            "regime": regime_name,
            "running": loop.running if loop else False,
            "paper_mode": loop.paper_mode if loop else None,
        },
        "session": {
            "status": _execution_state["session"]["status"],
            "mode": _execution_state["session"]["mode"],
            "symbol": _execution_state["session"]["symbol"],
            "session_id": _execution_state["session"]["session_id"],
        },
        "ws_client": {
            "connected": ws_connected,
            "symbols": ws_client.symbols if ws_client else [],
        },
        "position_manager": {
            "has_open": _execution_state["position_manager"].has_open(),
            "total_trades": len(_execution_state["trade_history"]),
        },
    }


@router.get("/opportunities")
async def get_opportunities(
    urgency: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get opportunities list with filters."""
    scheduler = await _get_opportunity_scheduler()

    urgency_enum = None
    if urgency:
        urgency_enum = OpportunityUrgency(urgency.upper())

    category_enum = None
    if category:
        category_enum = OpportunityCategory(category.lower())

    opportunities = scheduler.router.get_opportunities(
        urgency=urgency_enum,
        category=category_enum,
        limit=limit,
    )

    result = [
        {
            "id": opp.id,
            "symbol": opp.symbol,
            "category": opp.category.value,
            "urgency": opp.urgency.value,
            "source": opp.source.value,
            "title": opp.title,
            "description": opp.description,
            "url": opp.url,
            "is_tradeable": opp.is_tradeable,
            "confidence_score": opp.confidence_score,
            "published_at": opp.published_at.isoformat() if opp.published_at else None,
            "created_at": opp.created_at.isoformat(),
            "is_watched": opp.is_watched,
            "is_ignored": opp.is_ignored,
        }
        for opp in opportunities
    ]
    
    logger.info(
        f"GET /opportunities: {len(result)} opportunities returned "
        f"(filter urgency={urgency})"
    )
    
    return result


@router.post("/opportunities/{opportunity_id}/watchlist")
async def add_to_watchlist(opportunity_id: str) -> Dict:
    """Aggiunge simbolo a watchlist engine."""
    scheduler = await _get_opportunity_scheduler()

    for opp in scheduler.router._opportunities:
        if opp.id == opportunity_id and opp.symbol:
            if opp.symbol not in scheduler.router._watchlist:
                scheduler.router._watchlist.append(opp.symbol)
            opp.is_watched = True
            return {"status": "added", "symbol": opp.symbol}

    raise HTTPException(status_code=404, detail="Opportunity not found")


@router.post("/opportunities/{opportunity_id}/ignore")
async def ignore_opportunity(opportunity_id: str) -> Dict:
    """Marca un'opportunità come ignorata."""
    scheduler = await _get_opportunity_scheduler()

    if scheduler.router.mark_ignored(opportunity_id):
        return {"status": "ignored"}

    raise HTTPException(status_code=404, detail="Opportunity not found")


@router.get("/opportunities/watchlist")
async def get_opportunity_watchlist() -> List[str]:
    """Recupera la watchlist simboli."""
    scheduler = await _get_opportunity_scheduler()
    return scheduler.router.get_watchlist()


@router.get("/supervisor/history")
async def get_supervisor_history(session_id: str, limit: int = 50) -> List[Dict]:
    """Recupera le decisioni del supervisor per una sessione specifica."""
    try:
        db_sid = session_id
        cur = _execution_state.get("session", {})
        if cur.get("session_id") == session_id and cur.get("db_session_id"):
            db_sid = cur["db_session_id"]

        if not db_sid or db_sid == session_id and not _is_valid_uuid(db_sid):
            return []

        supabase = get_supabase()

        def _fetch():
            resp = supabase.table("supervisor_memory") \
                .select("*") \
                .eq("session_id", db_sid) \
                .order("decided_at", desc=True) \
                .limit(limit) \
                .execute()
            return resp.data if resp.data else []

        records = await asyncio.to_thread(_fetch)

        result = []
        for r in records:
            entry = {
                "action": r.get("action", "no_action"),
                "reason": r.get("reason", ""),
                "confidence": r.get("confidence", 0.0),
                "timestamp": r.get("decided_at"),
                "decided_at": r.get("decided_at"),
                "market_bias": r.get("market_bias"),
                "primary_signal": r.get("primary_signal"),
                "new_strategy": r.get("new_strategy"),
                "new_params": r.get("new_params"),
                "was_applied": r.get("was_applied", True),
                "blocked_reason": r.get("blocked_reason"),
            }
            result.append(entry)

        logger.info(
            f"GET /supervisor/history: {len(result)} records for session_id={session_id[:8]}..."
        )
        return result

    except Exception as e:
        logger.error(f"GET /supervisor/history error: {e}")
        return []
