import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from app.dependencies import get_current_user
from app.execution.schemas import StrategyRequest
from app.core.strategy_generator import generate_for_request
from app.db.supabase_client import get_supabase
from app.api.ws import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# In-memory store for generation status (TASK-050)
# In production, this should be in Redis or DB
generations: Dict[str, Dict[str, Any]] = {}

async def run_generation_task(generation_id: str, req: StrategyRequest):
    generations[generation_id]["status"] = "running"
    try:
        # TASK-FIX-006: WS progress — fetching market data
        await manager.broadcast({
            "type": "generation_progress",
            "generation_id": generation_id,
            "phase": "fetching_market_data",
            "message": "Scaricamento dati storici Binance (90 giorni)...",
        })

        # TASK-041/047: Generate strategies with real backtest
        strategies, empty_hint = await generate_for_request(req)

        # TASK-FIX-007 / HALU-BE-02: Handle empty list with user message (quality vs market data)
        if not strategies:
            generations[generation_id]["status"] = "completed"
            generations[generation_id]["results"] = []
            generations[generation_id]["message"] = empty_hint or (
                "Nessuna strategia disponibile. Modifica i parametri e riprova."
            )
            await manager.broadcast({
                "type": "generation_complete",
                "generation_id": generation_id,
                "count": 0,
            })
            return

        # TASK-FIX-006: WS progress — saving
        await manager.broadcast({
            "type": "generation_progress",
            "generation_id": generation_id,
            "phase": "saving",
            "message": f"Backtest completato: {len(strategies)} strategie valide. Salvataggio...",
        })

        db = get_supabase()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=7)).isoformat()

        # Salva subito sul DB per persistenza tra le pagine
        strategies_data = []
        for s in strategies:
            strategy_id = str(uuid.uuid4())
            # TASK-FIX-005: Save backtest fields in DB row
            row = {
                "id": strategy_id,
                "title": s.title or f"{s.template} on {s.pair}",
                "description": s.description,
                "template": s.template,
                "pair": s.pair,
                "timeframe": s.timeframe,
                "budget_eur": s.budget_eur,
                "params": s.params,
                "rules": {},
                "risk": {},
                "targets": {},
                "status": "PENDING",
                "score": s.score,                          # REALE (era 0.0 hardcoded)
                "ai_score": s.score,                       # REALE (era s.ai_score random)
                "estimated_profit_pct": s.estimated_profit_pct,  # REALE
                "estimated_profit_eur": s.estimated_profit_eur,  # REALE
                "backtest": {                               # NUOVO — popolato con dati reali
                    "pnl_pct":          s.backtest_pnl,
                    "win_rate":         s.backtest_win_rate,
                    "sharpe":           s.backtest_sharpe,
                    "max_drawdown_pct": s.backtest_drawdown,
                    "num_trades":       s.backtest_trades,
                    "data_source":      s.data_source,
                },
                "custom_name": s.custom_name,
                "created_at": now.isoformat(),
                "expires_at": expires_at
            }
            try:
                db.table("strategies").insert(row).execute()
            except Exception as e:
                logger.warning(f"Failed to save generated strategy to DB: {e}")

            strategies_data.append({
                "id": strategy_id,
                "template": s.template,
                "title": s.title,
                "description": s.description,
                "pair": s.pair,
                "timeframe": s.timeframe,
                "params": s.params,
                "budget_eur": s.budget_eur,
                "score": s.score,
                "ai_score": s.score,
                "estimated_profit_pct": s.estimated_profit_pct,
                "estimated_profit_eur": s.estimated_profit_eur,
                "backtest": {
                    "pnl_pct":          s.backtest_pnl,
                    "win_rate":         s.backtest_win_rate,
                    "sharpe":           s.backtest_sharpe,
                    "max_drawdown_pct": s.backtest_drawdown,
                    "num_trades":       s.backtest_trades,
                    "data_source":      s.data_source,
                },
                "custom_name": s.custom_name,
                "expires_at": expires_at,
                "created_at": now.isoformat(),
                "status": "PENDING"
            })

        generations[generation_id]["status"] = "completed"
        generations[generation_id]["results"] = strategies_data

        # TASK-053: Broadcast WS completion
        await manager.broadcast({
            "type": "generation_complete",
            "generation_id": generation_id,
            "count": len(strategies_data)
        })

    except Exception as e:
        generations[generation_id]["status"] = "failed"
        generations[generation_id]["error"] = str(e)
        await manager.broadcast({
            "type": "generation_failed",
            "generation_id": generation_id,
            "error": str(e)
        })

@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def start_generation(
    req: StrategyRequest,
    background_tasks: BackgroundTasks,
    _user: str = Depends(get_current_user) # TASK-051
):
    """
    TASK-048: POST /api/pipeline/generate
    TASK-049: Return 202 Accepted with generation_id
    """
    generation_id = str(uuid.uuid4())
    generations[generation_id] = {
        "status": "pending",
        "results": []
    }

    background_tasks.add_task(run_generation_task, generation_id, req)

    return {"generation_id": generation_id, "status": "pending"}

@router.get("/generate/{generation_id}/status")
async def get_generation_status(
    generation_id: str,
    _user: str = Depends(get_current_user) # TASK-051
):
    """
    TASK-050: GET status
    """
    if generation_id not in generations:
        raise HTTPException(status_code=404, detail="Generation not found")

    return generations[generation_id]