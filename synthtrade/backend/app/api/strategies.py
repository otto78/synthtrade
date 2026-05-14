from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from app.dependencies import get_current_user, get_exchange
from app.api.ws import manager
from app.db.supabase_client import get_supabase
from app.core.market_data import get_current_price
from app.execution.capital_allocator import CapitalAllocator, BudgetTooSmallError
from app.execution.quantity_calculator import calculate_quantity
from pydantic import BaseModel
import logging
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])

class StrategyCreate(BaseModel):
    template: str
    pair: str
    timeframe: str
    params: dict
    budget_eur: float = 100.0
    title: str | None = None
    description: str | None = None
    created_at: str | None = None
    expires_at: str | None = None

@router.get("")
def list_strategies(
    strategy_status: str | None = Query(None, description="OPEN | CLOSED"),
    _: str = Depends(get_current_user),
):
    db = get_supabase()
    
    # Transizione automatica: ACTIVE scadute → EXPIRED
    try:
        now = datetime.now(timezone.utc).isoformat()
        db.table("strategies").update({"status": "EXPIRED"}).eq("status", "ACTIVE").lt("expires_at", now).execute()
    except Exception as e:
        logger.warning(f"Expiry transition failed: {e}")
    
    # Pulizia: PENDING scadute → cancellate
    try:
        now = datetime.now(timezone.utc).isoformat()
        db.table("strategies").delete().eq("status", "PENDING").lt("expires_at", now).execute()
    except Exception as e:
        logger.warning(f"Auto-cleanup failed: {e}")
    
    query = db.table("strategies").select("id,title,custom_name,description,template,pair,timeframe,score,status,ai_score,ai_risk,budget_eur,params,estimated_profit_pct,estimated_profit_eur,ai_note,ai_strengths,ai_warnings,expires_at,created_at,updated_at")
    if strategy_status:
        query = query.eq("status", strategy_status)
    res = query.execute()
    return res.data


@router.get("/active/pnl")
def get_active_strategies_pnl(_: str = Depends(get_current_user)):
    """
    TASK-416: GET /api/strategies/active/pnl
    Restituisce P&L live per tutte le strategie ACTIVE
    """
    db = get_supabase()
    res = db.table("strategies").select("*").eq("status", "ACTIVE").execute()
    active_strategies = res.data or []
    
    pnl_data = []
    for strategy in active_strategies:
        strategy_id = strategy["id"]
        # Recupera trade OPEN per questa strategia
        trades_res = db.table("trades").select("*").eq("strategy_id", strategy_id).eq("status", "OPEN").execute()
        open_trades = trades_res.data or []
        
        if not open_trades:
            continue
            
        # Calcola P&L totale
        total_pnl_pct = 0.0
        total_pnl_eur = 0.0
        initial_capital = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
        
        for trade in open_trades:
            entry_price = float(trade.get("price", 0))
            qty = float(trade.get("quantity", 0))
            current_price = get_current_price(trade["pair"])
            if trade["action"] == "BUY":
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            pnl_eur = (pnl_pct / 100) * initial_capital
            total_pnl_pct += pnl_pct
            total_pnl_eur += pnl_eur
        
        avg_pnl_pct = total_pnl_pct / len(open_trades) if open_trades else 0.0
        current_value = initial_capital + total_pnl_eur
        
        pnl_data.append({
            "id": strategy_id,
            "title": strategy.get("title", ""),
            "avg_pnl_pct": round(avg_pnl_pct, 4),
            "total_pnl_pct": round(total_pnl_pct, 4),
            "current_value_usdt": round(current_value, 2),
            "open_trades_count": len(open_trades)
        })
    
    return {"active_strategies_pnl": pnl_data}

@router.post("")
def create_strategy(strategy: StrategyCreate, _user: str = Depends(get_current_user)):
    db = get_supabase()
    
    # Calcolo data di scadenza (7 giorni da ora)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    # Mappatura dei dati per far corrispondere lo schema Supabase (TASK-321 Scadenza)
    data = {
        "id": str(uuid.uuid4()),
        "title": strategy.title or f"{strategy.template} on {strategy.pair}",
        "description": strategy.description,
        "template": strategy.template,
        "pair": strategy.pair,
        "timeframe": strategy.timeframe,
        "budget_eur": strategy.budget_eur,
        "params": strategy.params,
        "rules": {}, 
        "risk": {}, 
        "targets": {}, 
        "status": "PENDING",
        "score": 0.0,
        "ai_score": 0.0,
        "created_at": strategy.created_at or now.isoformat(),
        "expires_at": strategy.expires_at or expires_at.isoformat()
    }
    
    logger.info(f"Creating strategy with expiry: {data['title']} (expires: {data['expires_at']})")
    
    try:
        res = db.table("strategies").insert(data).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create strategy: DB returned no data")
        return res.data[0]
    except Exception as e:
        logger.error(f"Error during strategy creation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{strategy_id}")
def get_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("*").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return res.data[0]

@router.post("/{strategy_id}/approve")
def approve_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    logger.info(f"Approving strategy {strategy_id}")
    db = get_supabase()
    try:
        res = db.table("strategies").select("id,status").eq("id", strategy_id).execute()
        logger.info(f"Found strategy in DB: {res.data}")
        if not res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        
        update_res = db.table("strategies").update({"status": "APPROVED"}).eq("id", strategy_id).execute()
        logger.info(f"Update result: {update_res.data}")
        if not update_res.data:
            # Tentativo fallback se l'ID è un UUID stringa ma il DB si aspetta altro o viceversa
            logger.info(f"Retrying with explicit ID match")
            update_res = db.table("strategies").update({"status": "APPROVED"}).match({"id": strategy_id}).execute()
            logger.info(f"Fallback update result: {update_res.data}")
            
        return {"id": strategy_id, "status": "APPROVED"}
    except Exception as e:
        logger.error(f"Error during strategy approval: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{strategy_id}/reject")
def reject_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("id,status").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    db.table("strategies").update({"status": "REJECTED"}).eq("id", strategy_id).execute()
    return {"id": strategy_id, "status": "REJECTED"}

@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    request: Request,
    _user: str = Depends(get_current_user),
    exchange = Depends(get_exchange),
):
    db = get_supabase()
    res = db.table("strategies").select("*").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    strategy = res.data[0]
    allowed_statuses = {"APPROVED", "PENDING"}
    if strategy["status"] not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Strategia non attivabile dallo stato '{strategy['status']}'. "
                   f"Richiesto: {allowed_statuses}"
        )

    budget_usdt = float(strategy.get("budget_eur") or 100.0)

    # 1. Controlla fondi disponibili
    try:
        available_usdt = await exchange.get_balance()
        holdings = await exchange.get_holdings()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Exchange non raggiungibile: {e}")

    # TASK-403: Verifica fondi sufficienti (tolleranza 5%)
    if available_usdt < budget_usdt * 0.95:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "insufficient_funds",
                "available": round(available_usdt, 2),
                "required": round(budget_usdt, 2),
            }
        )

    # 2. Calcola trade iniziali
    allocator = CapitalAllocator()
    strategy["initial_capital_usdt"] = budget_usdt
    try:
        trade_requests = allocator.allocate(strategy, available_usdt, holdings)
    except BudgetTooSmallError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "budget_too_small", "symbol": e.symbol,
                    "required": e.required_usdt, "available": e.available_usdt}
        )

    # 3. Piazza i trade iniziali
    allocation_trades = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    for trade_req in trade_requests:
        try:
            # Calcola quantità: usdt_amount / prezzo corrente
            price = await exchange.get_ticker_price(trade_req.symbol)
            filters = await exchange.get_symbol_filters(trade_req.symbol)
            qty = calculate_quantity(
                budget_usdt=trade_req.usdt_amount,
                price=price,
                filters=filters,
            )
            result = await exchange.place_market_order(trade_req.symbol, trade_req.side, qty)

            trade_row = {
                "strategy_id": strategy_id,
                "pair": trade_req.symbol,
                "action": trade_req.side.upper(),
                "price": result.get("price") or price,
                "quantity": result.get("quantity") or qty,
                "trade_type": "INITIAL_ALLOCATION",
                "status": "OPEN",
                "paper": True,
                "executed_at": now.isoformat(),
            }
            db_res = db.table("trades").insert(trade_row).execute()
            
            # TASK-414: Broadcast real-time
            if db_res.data:
                trade_id = db_res.data[0]["id"]
                await manager.broadcast_trade_opened(
                    strategy_id=strategy_id,
                    trade_id=trade_id,
                    symbol=trade_req.symbol,
                    direction=trade_req.side.upper(),
                    price=trade_row["price"],
                    quantity=trade_row["quantity"]
                )
                
            allocation_trades.append({"symbol": trade_req.symbol, "pct": trade_req.pct,
                                      "usdt": trade_req.usdt_amount, "qty": qty, "price": price})

        except Exception as e:
            # Rollback: riporta a APPROVED
            logger.error(f"Errore allocazione {trade_req.symbol}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Errore durante acquisto {trade_req.symbol}: {e}. "
                       "Strategia non attivata."
            )

    # 4. Aggiorna strategia con i dati di attivazione
    db.table("strategies").update({
        "status": "ACTIVE",
        "activated_at": now.isoformat(),
        "initial_capital_usdt": budget_usdt,
        "current_value_usdt": budget_usdt,
        "allocation_trades": allocation_trades,
    }).eq("id", strategy_id).execute()

    logger.info(f"Strategia {strategy_id} attivata: budget={budget_usdt} USDT, "
                f"{len(allocation_trades)} trade iniziali")
    return {
        "id": strategy_id,
        "status": "ACTIVE",
        "initial_capital_usdt": budget_usdt,
        "allocation_trades": allocation_trades,
    }


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: str,
    request: Request,
    _user: str = Depends(get_current_user),
):
    """
    TASK-411: Ferma una strategia ACTIVE.
    Chiude tutti i trade OPEN e aggiorna a STOPPED.
    """
    db = get_supabase()
    res = db.table("strategies").select("*").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    strategy = res.data[0]

    if strategy["status"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Strategia non attiva (stato: {strategy['status']}). Solo ACTIVE può essere fermata."
        )

    exchange = get_exchange(request)
    from app.api.ws import manager

    # Recupera trade OPEN e chiudi
    trades_res = db.table("trades").select("*").eq("strategy_id", strategy_id).eq("status", "OPEN").execute()
    open_trades = trades_res.data or []
    closed_count = 0
    errors = []

    for trade in open_trades:
        try:
            qty = trade.get("quantity", 0)
            if qty <= 0:
                continue
            result = await exchange.close_position(trade["pair"], "sell" if trade["action"] == "BUY" else "buy", qty)
            exit_price = result.get("price", 0)
            entry_price = trade.get("price", 0)
            pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0

            db.table("trades").update({
                "status": "CLOSED",
                "exit_price": exit_price,
                "pnl_pct": round(pnl_pct, 4),
                "trade_type": "STOP_CLOSE",
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", trade["id"]).execute()

            await manager.broadcast_trade_closed(
                strategy_id=strategy_id,
                trade_id=trade["id"],
                pnl_pct=pnl_pct,
                exit_price=exit_price,
            )
            closed_count += 1
        except Exception as e:
            logger.error(f"Errore chiusura trade {trade['id']}: {e}")
            errors.append(str(e))

    # Calcola P&L finale
    initial_capital = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 100.0)
    final_value = initial_capital  # default: no change
    total_pnl_pct = 0.0

    # Stima valore attuale da trade chiusi
    total_realized = 0.0
    for trade in open_trades:
        entry = trade.get("price", 0)
        qty = trade.get("quantity", 0)
        total_realized += entry * qty
    if total_realized > 0 and initial_capital > 0:
        total_pnl_pct = ((final_value - initial_capital) / initial_capital) * 100

    now_iso = datetime.now(timezone.utc).isoformat()
    db.table("strategies").update({
        "status": "STOPPED",
        "stopped_at": now_iso,
        "current_value_usdt": round(final_value, 2),
    }).eq("id", strategy_id).execute()

    await manager.broadcast_strategy_stopped(
        strategy_id=strategy_id,
        final_pnl_pct=total_pnl_pct,
        final_value_usdt=final_value,
    )

    logger.info(f"Strategia {strategy_id} fermata: {closed_count} trade chiusi, {len(errors)} errori")
    return {
        "id": strategy_id,
        "status": "STOPPED",
        "closed_trades": closed_count,
        "errors": errors if errors else None,
    }


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("id,status").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    db.table("strategies").delete().eq("id", strategy_id).execute()
    logger.info(f"Deleted strategy {strategy_id}")
    return {"id": strategy_id, "status": "DELETED"}
