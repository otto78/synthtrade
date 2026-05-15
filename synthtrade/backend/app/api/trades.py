from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from app.dependencies import get_current_user, get_trade_repo
from app.db.supabase_client import get_supabase
from app.db.repositories.trade_repository import TradeRepository
from app.models.trade import Trade

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=List[Trade])
def get_trades(
    status: Optional[str] = Query(None, description="OPEN | CLOSED"),
    limit: int = Query(50, ge=1, le=200),
    _: str = Depends(get_current_user),
    repo: TradeRepository = Depends(get_trade_repo),
):
    return repo.list_all(status=status, limit=limit)


@router.get("/open", response_model=List[Trade])
def get_open_positions(
    _: str = Depends(get_current_user),
    repo: TradeRepository = Depends(get_trade_repo),
):
    return repo.list_all(status="OPEN")


@router.get("/active")
def get_active_trades_with_join(
    _: str = Depends(get_current_user),
    repo: TradeRepository = Depends(get_trade_repo),
):
    """
    TASK-417: GET /api/trades/active con JOIN
    Restituisce trade attivi (status=OPEN) con dettagli della strategia associata
    """
    return repo.list_active_with_strategies()
