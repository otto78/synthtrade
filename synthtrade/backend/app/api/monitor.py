import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/{strategy_id}")
def get_strategy_monitor(strategy_id: str, _user: str = Depends(get_current_user)):
    """
    TASK-324: Recupera i dati di monitoraggio in tempo reale per una strategia.
    Include performance, statistiche operative e lista trade recenti.
    """
    db = get_supabase()
    
    # 1. Recupera info base strategia
    strategy_res = db.table("strategies").select("*").eq("id", strategy_id).execute()
    if not strategy_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    
    strategy = strategy_res.data[0]
    
    # 2. Recupera trade associati per calcolare statistiche reali
    trades_res = db.table("trades").select("*").eq("strategy_id", strategy_id).order("executed_at", desc=True).execute()
    trades = trades_res.data or []
    
    # 3. Calcola statistiche operative reali
    total_trades = len(trades)
    closed_trades = [t for t in trades if t["status"] == "CLOSED"]
    winning_trades = [t for t in closed_trades if (t.get("pnl_pct") or 0) > 0]
    
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
    total_pnl_pct = sum((t.get("pnl_pct") or 0) for t in trades)
    
    # 4. Costruisci equity curve basata sui trade (semplificata per ora)
    equity_curve = [100.0] # Base 100
    current_equity = 100.0
    for t in reversed(trades): # Dal più vecchio al più recente
        if t["status"] == "CLOSED":
            current_equity *= (1 + (t.get("pnl_pct") or 0))
            equity_curve.append(round(current_equity, 2))

    return {
        "strategy": {
            "id": strategy["id"],
            "title": strategy["title"],
            "status": strategy["status"],
            "pair": strategy["pair"],
            "timeframe": strategy["timeframe"]
        },
        "stats": {
            "total_pnl_pct": round(total_pnl_pct * 100, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,
            "active_trades": len([t for t in trades if t["status"] == "OPEN"]),
            "equity_curve": equity_curve
        },
        "recent_trades": trades[:10] # Ultimi 10 trade
    }
