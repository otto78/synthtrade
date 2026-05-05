from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/strategies", tags=["strategies"])


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
