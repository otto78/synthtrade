"""Historical Context Builder - reads aggregated performance from database.

Livello 2: Context Builder storico per Supervisor AI.
Legge la vista signal_outcome_by_strategy_regime e produce un dict strutturato
da iniettare nel prompt del supervisor per apprendimento dai dati passati.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache per evitare query ad ogni tick del supervisor
_historical_cache: Optional[Dict] = None
_cache_timestamp: Optional[datetime] = None
_CACHE_TTL_MINUTES = 5


async def build_historical_context() -> Dict:
    """Build historical context from signal_outcome_by_strategy_regime view.
    
    Reads aggregated win rate data from Supabase and structures it for the supervisor.
    Uses 5-minute cache to avoid querying on every tick.
    
    Returns:
        Dict with historical performance data:
        {
            "historical_performance": {
                "rsi_bollinger/ranging": {"n_trades": 30, "win_rate_pct": 43.3, "avg_pnl": -0.12},
            },
            "best_combination": "rsi_bollinger/ranging",
            "worst_combination": "ema_cross/trending_down",
            "total_historical_trades": 70,
            "data_freshness": "2026-06-29T14:30:00Z"
        }
    """
    global _historical_cache, _cache_timestamp
    
    # Check cache
    now = datetime.utcnow()
    if _historical_cache and _cache_timestamp:
        cache_age = now - _cache_timestamp
        if cache_age < timedelta(minutes=_CACHE_TTL_MINUTES):
            logger.debug(f"Historical context: using cache (age: {cache_age.total_seconds():.0f}s)")
            return _historical_cache
    
    try:
        from app.db.supabase_client import get_supabase
        
        def _fetch_historical_data():
            supabase = get_supabase()
            resp = supabase.table("signal_outcome_by_strategy_regime") \
                .select("*") \
                .execute()
            return resp.data if resp.data else []
        
        data = await asyncio.to_thread(_fetch_historical_data)
        
        if not data:
            logger.warning("Historical context: no data from signal_outcome_by_strategy_regime")
            return _get_empty_context()
        
        # Process data
        historical_performance = {}
        total_trades = 0
        best_combination = None
        worst_combination = None
        best_win_rate = -1.0
        worst_win_rate = 101.0
        
        for row in data:
            strategy_type = row.get("strategy_type", "unknown")
            regime = row.get("regime", "unknown")
            n_trades = row.get("n_trades", 0)
            win_rate_pct = row.get("win_rate_pct", 0.0)
            avg_pnl = row.get("avg_pnl", 0.0)
            
            if n_trades < 5:
                # Campione insufficiente - skip o marca come insufficient
                key = f"{strategy_type}/{regime}"
                historical_performance[key] = {
                    "n_trades": n_trades,
                    "win_rate_pct": win_rate_pct,
                    "avg_pnl": avg_pnl,
                    "insufficient_data": True
                }
                continue
            
            total_trades += n_trades
            key = f"{strategy_type}/{regime}"
            historical_performance[key] = {
                "n_trades": n_trades,
                "win_rate_pct": win_rate_pct,
                "avg_pnl": avg_pnl
            }
            
            # Track best/worst
            if win_rate_pct > best_win_rate:
                best_win_rate = win_rate_pct
                best_combination = key
            if win_rate_pct < worst_win_rate:
                worst_win_rate = win_rate_pct
                worst_combination = key
        
        # Build result
        result = {
            "historical_performance": historical_performance,
            "best_combination": best_combination,
            "worst_combination": worst_combination,
            "total_historical_trades": total_trades,
            "data_freshness": now.isoformat()
        }
        
        # Update cache
        _historical_cache = result
        _cache_timestamp = now
        
        logger.info(f"Historical context: loaded {len(historical_performance)} combinations, {total_trades} total trades")
        return result
        
    except Exception as e:
        logger.error(f"Historical context: failed to load data: {e}")
        return _get_empty_context()


def _get_empty_context() -> Dict:
    """Return empty context when no data is available."""
    return {
        "historical_performance": {},
        "best_combination": None,
        "worst_combination": None,
        "total_historical_trades": 0,
        "data_freshness": datetime.utcnow().isoformat()
    }


def clear_historical_cache() -> None:
    """Clear the historical context cache.
    
    Useful for testing or when fresh data is needed immediately.
    """
    global _historical_cache, _cache_timestamp
    _historical_cache = None
    _cache_timestamp = None
    logger.info("Historical context cache cleared")