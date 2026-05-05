from datetime import date
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase
from app.core.market_data import get_current_price

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(_user: str = Depends(get_current_user)):
    db = get_supabase()
    today = date.today().isoformat()

    trades = (db.table("trades")
               .select("pnl_pct,cost_eur")
               .gte("executed_at", today)
               .execute()).data or []

    pnl_today = round(
        sum((t.get("pnl_pct") or 0) * (t.get("cost_eur") or 0) for t in trades), 4
    )

    active = (db.table("strategies")
               .select("id,title,score,status")
               .eq("status", "ACTIVE")
               .limit(1)
               .execute()).data

    try:
        price = get_current_price("BTC/USDT")
        balance = price
    except Exception:
        balance = 0.0

    return {
        "balance": balance,
        "pnl_today": pnl_today,
        "active_strategy": active[0] if active else None,
        "engine_status": "RUNNING",
    }


@router.get("/equity-history")
def get_equity_history(_user: str = Depends(get_current_user)):
    db = get_supabase()
    rows = (db.table("trades")
             .select("executed_at,cost_eur,pnl_pct")
             .order("executed_at")
             .execute()).data or []

    return [
        {
            "ts": r["executed_at"],
            "value": round((r.get("cost_eur") or 0) * (1 + (r.get("pnl_pct") or 0)), 4),
        }
        for r in rows
    ]
