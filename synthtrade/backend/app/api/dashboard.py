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
from app.models.trade import Trade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

BALANCE_TIMEOUT = 30


def _mode_filter(query):
    """Aggiunge filtro trading_mode a query Supabase diretta."""
    return query.eq("trading_mode", settings.TRADING_MODE)


@router.get("")
async def get_dashboard(
    _user: str = Depends(get_current_user),
    strategy_repo: StrategyRepository = Depends(get_strategy_repo),
    trade_repo: TradeRepository = Depends(get_trade_repo),
):
    db = get_supabase()
    today = date.today().isoformat()

    # ——— TRADES OGGI (con trading_mode filter) ———
    trades = trade_repo.get_since(today)

    pnl_today = 0.0
    for t in trades:
        if t.pnl_eur:
            pnl_today += t.pnl_eur
        elif t.pnl_pct and t.price and t.quantity:
            estimated_pnl = (t.price * t.quantity) * abs(t.pnl_pct) / 100
            pnl_today += estimated_pnl
    pnl_today = round(pnl_today, 4)

    # ——— KPI: strategie attive (con trading_mode filter) ———
    active_strategies_res = _mode_filter(
        db.table("strategies").select("*").eq("status", "ACTIVE")
    ).execute()
    active_strategies = active_strategies_res.data or []
    active_strategies_count = len(active_strategies)

    # ——— KPI: trade aperti (con trading_mode filter) ———
    open_trades_res = _mode_filter(
        db.table("trades").select("id").eq("status", "OPEN")
    ).execute()
    open_trades_count = len(open_trades_res.data or [])

    # ——— PnL strategie attive (solo calcolo percentuale) ———
    total_active_pnl_pct = 0.0
    for strategy in active_strategies:
        current = strategy.get("current_value_usdt")
        initial = strategy.get("initial_capital_usdt") or strategy.get("budget_eur")
        if current and initial and initial > 0:
            pnl_pct = ((current - initial) / initial) * 100
            total_active_pnl_pct += pnl_pct
    total_active_pnl_pct = round(total_active_pnl_pct, 2)

    # ——— Saldo exchange (provider-neutral) ———
    balance_eur = 0.0
    balance_breakdown = {}
    balance_assets = []

    try:
        provider = settings.EXCHANGE_PROVIDER.lower()
        if provider == "okx":
            from app.core.okx_balance import get_total_balance_eur as _get_balance
        else:
            from app.core.binance_balance import get_total_balance_eur as _get_balance

        balance_info = await asyncio.wait_for(
            asyncio.to_thread(_get_balance),
            timeout=BALANCE_TIMEOUT
        )
        balance_eur = balance_info.get("total_eur", 0.0)
        balance_breakdown = balance_info.get("breakdown", {})
        balance_assets = balance_info.get("assets", [])

        if balance_eur <= 0:
            logger.warning("%s balance is 0 or failed to fetch", provider.upper())

    except asyncio.TimeoutError:
        logger.warning(f"Balance fetch timed out after {BALANCE_TIMEOUT}s")
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")

    # ——— KPI: trade chiusi oggi ———
    closed_trades_count = 0
    closed_trades_pnl = 0.0
    try:
        closed_trades_today_res = _mode_filter(
            db.table("trades").select("pnl_pct,price,quantity,fee_eur").eq("status", "CLOSED").gte("closed_at", today)
        ).execute()
        closed_trades_count = len(closed_trades_today_res.data or [])
        closed_trades_pnl = 0.0
        for t in closed_trades_today_res.data or []:
            if t.get("pnl_pct") and t.get("price") and t.get("quantity"):
                closed_trades_pnl += (t["price"] * t["quantity"]) * abs(t["pnl_pct"]) / 100
        closed_trades_pnl = round(closed_trades_pnl, 2)
    except Exception:
        logger.warning("Dashboard: DB query for closed trades failed (non-critical, showing 0)")

    return {
        "balance": balance_eur,
        "balance_eur": balance_eur,
        "balance_breakdown": balance_breakdown,
        "balance_assets": balance_assets,
        "pnl_today": pnl_today,
        "active_strategies_count": active_strategies_count,
        "open_trades_count": open_trades_count,
        "closed_trades_count": closed_trades_count,
        "closed_trades_pnl": closed_trades_pnl,
        "total_active_pnl_pct": total_active_pnl_pct,
        "engine_status": "RUNNING",
        "trading_mode": settings.TRADING_MODE,
        "exchange_provider": settings.EXCHANGE_PROVIDER.lower(),
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