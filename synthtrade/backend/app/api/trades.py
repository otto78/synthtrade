from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("")
def get_trades(
    status: Optional[str] = Query(None, description="OPEN | CLOSED"),
    limit: int = Query(50, ge=1, le=200),
    _: str = Depends(get_current_user),
):
    db = get_supabase()
    query = db.table("trades").select("*")
    if status:
        query = query.eq("status", status)
    res = query.order("executed_at", desc=True).execute()
    return res.data[:limit]


@router.get("/open")
def get_open_positions(_: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("trades").select("*").eq("status", "OPEN") \
            .order("executed_at", desc=True).execute()
    return res.data
