from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.dependencies import get_current_user, get_exchange
from app.db.supabase_client import get_supabase
from app.execution.capital_allocator import CapitalAllocator, BudgetTooSmallError
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
    strategy_status: str | None = None,
    _user: str = Depends(get_current_user),
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
):
    """
    TASK-402: Attiva una strategia con allocazione capitale reale.
    1. Verifica stato (deve essere APPROVED o PENDING)
    2. Controlla fondi USDT disponibili
    3. Alloca capitale acquistando le crypto necessarie
    4. Salva activated_at e initial_capital_usdt
    """
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

    exchange = get_exchange(request)
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
            from app.execution.quantity_calculator import calculate_quantity
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
            db.table("trades").insert(trade_row).execute()
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
    TASK-411: Ferma una strategia chiudendo tutti i trade aperti (best-effort).
    """
    db = get_supabase()
    res = db.table("strategies").select("*").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    strategy = res.data[0]
    if strategy["status"] == "STOPPED":
        raise HTTPException(status_code=409, detail="Strategia già ferma")
    if strategy["status"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Solo strategie ACTIVE possono essere fermate (stato attuale: {strategy['status']})"
        )

    exchange = get_exchange(request)

    # Recupera tutti i trade aperti di questa strategia
    trades_res = db.table("trades").select("*").eq("strategy_id", strategy_id).eq("status", "OPEN").execute()
    open_trades = trades_res.data or []

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    close_errors = []
    total_pnl_pct = 0.0
    closed_count = 0

    for trade in open_trades:
        try:
            symbol = trade["pair"]
            direction = trade["action"]  # BUY o SELL
            quantity = float(trade["quantity"])
            entry_price = float(trade["price"])

            # Chiudi la posizione
            result = await exchange.close_position(symbol, direction, quantity)
            exit_price = float(result.get("price") or await exchange.get_ticker_price(symbol))

            # Calcola P&L
            if direction == "BUY":
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - exit_price) / entry_price
            total_pnl_pct += pnl_pct

            db.table("trades").update({
                "status": "CLOSED",
                "exit_price": exit_price,
                "pnl_pct": round(pnl_pct * 100, 4),
                "trade_type": "STOP_CLOSE",
                "closed_at": now.isoformat(),
            }).eq("id", trade["id"]).execute()
            closed_count += 1

        except Exception as e:
            logger.error(f"Errore chiusura trade {trade['id']}: {e}")
            close_errors.append({"trade_id": trade["id"], "error": str(e)})

    # Calcola valore finale
    initial = float(strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 0)
    avg_pnl_pct = (total_pnl_pct / closed_count * 100) if closed_count > 0 else 0.0
    final_value = initial * (1 + total_pnl_pct) if closed_count > 0 else initial

    # Aggiorna strategia
    db.table("strategies").update({
        "status": "STOPPED",
        "stopped_at": now.isoformat(),
        "current_value_usdt": round(final_value, 2),
    }).eq("id", strategy_id).execute()

    # Broadcast WebSocket
    try:
        from app.api.ws import manager
        await manager.broadcast({
            "type": "strategy_stopped",
            "strategy_id": strategy_id,
            "final_pnl_pct": round(avg_pnl_pct, 2),
            "final_value_usdt": round(final_value, 2),
            "closed_trades": closed_count,
            "errors": len(close_errors),
        })
    except Exception as e:
        logger.warning(f"WS broadcast strategy_stopped fallito: {e}")

    logger.info(f"Strategia {strategy_id} fermata: {closed_count} trade chiusi, "
                f"P&L medio {avg_pnl_pct:.2f}%")
    return {
        "id": strategy_id,
        "status": "STOPPED",
        "closed_trades": closed_count,
        "final_pnl_pct": round(avg_pnl_pct, 2),
        "final_value_usdt": round(final_value, 2),
        "errors": close_errors if close_errors else None,
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
