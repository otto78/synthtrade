from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase
from pydantic import BaseModel

router = APIRouter(prefix="/strategies", tags=["strategies"])

class StrategyCreate(BaseModel):
    template: str
    pair: str
    timeframe: str
    params: dict
    budget_eur: float = 100.0

@router.get("")
def list_strategies(
    strategy_status: str | None = None,
    _user: str = Depends(get_current_user),
):
    db = get_supabase()
    query = db.table("strategies").select("id,title,score,status,ai_score,ai_risk")
    if strategy_status:
        query = query.eq("status", strategy_status)
    res = query.execute()
    return res.data

@router.post("")
def create_strategy(strategy: StrategyCreate, _user: str = Depends(get_current_user)):
    db = get_supabase()
    data = {
        "title": f"{strategy.template} on {strategy.pair}",
        "template": strategy.template,
        "pair": strategy.pair,
        "timeframe": strategy.timeframe,
        "params": strategy.params,
        "status": "PENDING",
        "score": 0,
        "ai_score": 0
    }
    res = db.table("strategies").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create strategy")
    return res.data[0]

@router.get("/{strategy_id}")
def get_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("*").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return res.data[0]

@router.post("/{strategy_id}/approve")
def approve_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("id,status").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if res.data[0]["status"] != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Strategy is not PENDING")
    db.table("strategies").update({"status": "APPROVED"}).eq("id", strategy_id).execute()
    return {"id": strategy_id, "status": "APPROVED"}

@router.post("/{strategy_id}/reject")
def reject_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("id,status").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    db.table("strategies").update({"status": "REJECTED"}).eq("id", strategy_id).execute()
    return {"id": strategy_id, "status": "REJECTED"}
