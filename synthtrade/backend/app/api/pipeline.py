import uuid
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from app.dependencies import get_current_user
from app.execution.schemas import StrategyRequest
from app.core.strategy_generator import generate_for_request
from app.api.ws import manager

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# In-memory store for generation status (TASK-050)
# In production, this should be in Redis or DB
generations: Dict[str, Dict[str, Any]] = {}

async def run_generation_task(generation_id: str, req: StrategyRequest):
    generations[generation_id]["status"] = "running"
    try:
        # TASK-041/047: Generate strategies
        strategies = await generate_for_request(req)
        
        # Convert StrategyParams to dict for storage/API
        strategies_data = []
        for s in strategies:
            strategies_data.append({
                "template": s.template,
                "title": s.title,
                "description": s.description,
                "pair": s.pair,
                "timeframe": s.timeframe,
                "params": s.params,
                "budget_eur": s.budget_eur,
                "ai_score": s.ai_score,
                "estimated_profit_pct": s.estimated_profit_pct,
                "estimated_profit_eur": s.estimated_profit_eur
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
