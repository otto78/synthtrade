import logging
import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, Query
from app.config import settings
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user, get_strategy_repo, get_trade_repo
from app.db.repositories.strategy_repository import StrategyRepository
from app.db.repositories.trade_repository import TradeRepository
from app.core.binance_balance import get_total_balance_eur
from app.models.trade import Trade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

BALANCE_TIMEOUT = 30


@router.get("")
async def get_dashboard(
    _user: str = Depends(get_current_user),
    strategy_repo: StrategyRepository = Depends(get_strategy_repo),
    trade_repo: TradeRepository = Depends(get_trade_repo),
):
    today = date.today().isoformat()

    trades = trade_repo.get_since(today)

    # Calcola PnL da pnl_pct * cost se pnl_eur è null
    pnl_today = 0.0
    for t in trades:
        if t.pnl_eur:
            pnl_today += t.pnl_eur
        elif t.pnl_pct and t.price and t.quantity:
            # Stima: pnl_eur ≈ price * quantity * pnl_pct
            estimated_pnl = (t.price * t.quantity) * abs(t.pnl_pct) / 100
            pnl_today += estimated_pnl

    pnl_today = round(pnl_today, 4)

    db = get_supabase()

    # KPI: strategie attive
    active_strategies_res = db.table("strategies").select("*").eq("status", "ACTIVE").execute()
    active_strategies = active_strategies_res.data or []
    active_strategies_count = len(active_strategies)

    # KPI: trade aperti (OPEN)
    open_trades_res = db.table("trades").select("id").eq("status", "OPEN").execute()
    open_trades_count = len(open_trades_res.data or [])

    # Calcola P&L totale da strategie attive e PnL portafoglio
    total_active_pnl_pct = 0.0
    total_invested = 0.0
    total_current = 0.0
    for strategy in active_strategies:
        initial = strategy.get("initial_capital_usdt") or strategy.get("budget_eur", 100.0)
        current = strategy.get("current_value_usdt") or strategy.get("initial_capital_usdt", 100.0)
        if initial > 0:
            pnl_pct = ((current - initial) / initial) * 100
            total_active_pnl_pct += pnl_pct
            total_invested += initial
            total_current += current

    total_active_pnl_pct = round(total_active_pnl_pct, 2)
    total_strategy_pnl_eur = round(total_current - total_invested, 2)

    # Saldo Binance
    balance_eur = 0.0
    balance_breakdown = {}
    balance_assets = []

    try:
        balance_info = await asyncio.wait_for(
            asyncio.to_thread(get_total_balance_eur),
            timeout=BALANCE_TIMEOUT
        )
        balance_eur = balance_info.get("total_eur", 0.0)
        balance_breakdown = balance_info.get("breakdown", {})
        balance_assets = balance_info.get("assets", [])

        if balance_eur <= 0:
            logger.warning("Binance balance is 0 or failed to fetch — showing real balance (0.0)")

    except asyncio.TimeoutError:
        logger.warning(f"Binance balance fetch timed out after {BALANCE_TIMEOUT}s")
    except Exception as e:
        logger.error(f"Failed to fetch Binance balance: {e}")

    # PnL portafoglio: differenza tra saldo Binance e capitale investito
    if total_invested > 0 and balance_eur > 0:
        portfolio_pnl_eur = round(balance_eur - total_invested, 2)
        portfolio_pnl_pct = round(((balance_eur - total_invested) / total_invested) * 100, 2)
    else:
        portfolio_pnl_eur = 0.0
        portfolio_pnl_pct = 0.0

    return {
        "balance": balance_eur,
        "balance_eur": balance_eur,
        "balance_breakdown": balance_breakdown,
        "balance_assets": balance_assets,
        "pnl_today": pnl_today,
        "active_strategies_count": active_strategies_count,
        "open_trades_count": open_trades_count,
        "total_active_pnl_pct": total_active_pnl_pct,
        "total_strategy_pnl_eur": total_strategy_pnl_eur,
        "portfolio_pnl_eur": portfolio_pnl_eur,
        "portfolio_pnl_pct": portfolio_pnl_pct,
        "engine_status": "RUNNING",
        "trading_mode": settings.TRADING_MODE,
    }


@router.get("/equity-history")
def get_equity_history(
    _user: str = Depends(get_current_user),
    trade_repo: TradeRepository = Depends(get_trade_repo),
    range: str = Query("1m", description="Time range: 1d, 1w, 1m, 1y"),
):
    """Restituisce storico equity curve filtrato per timeframe."""
    now = datetime.now(timezone.utc)

    # Mappa range a data di inizio
    range_map = {
        "1d": now - timedelta(days=1),
        "1w": now - timedelta(weeks=1),
        "1m": now - timedelta(days=30),
        "1y": now - timedelta(days=365),
    }
    since = range_map.get(range, now - timedelta(days=30))
    since_iso = since.isoformat()

    rows = trade_repo.get_history()

    # Filtra per data e costruisci equity curve cumulativa
    cumulative = 0.0
    result = []
    for r in rows:
        ts = r.get("executed_at")
        if not ts or ts < since_iso:
            continue
        cost = r.get("cost_eur") or 0
        pnl = r.get("pnl_pct") or 0
        trade_value = cost * (1 + pnl)
        cumulative += trade_value - cost
        result.append({
            "ts": ts,
            "value": round(cumulative, 4),
        })

    # Se non ci sono trades, restituisci equity a 0
    if not result:
        result.append({
            "ts": since_iso,
            "value": 0,
        })
        result.append({
            "ts": now.isoformat(),
            "value": 0,
        })

    return result