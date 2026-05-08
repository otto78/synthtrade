from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase
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

    query = db.table("strategies").select("id,title,description,template,pair,timeframe,score,status,ai_score,ai_risk,budget_eur,params,estimated_profit_pct,estimated_profit_eur,ai_note,ai_strengths,ai_warnings,expires_at,created_at,updated_at")
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
def activate_strategy(strategy_id: str, _user: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("strategies").select("id,status").eq("id", strategy_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    # Una strategia può essere attivata solo se APPROVED o PENDING
    db.table("strategies").update({"status": "ACTIVE"}).eq("id", strategy_id).execute()
    return {"id": strategy_id, "status": "ACTIVE"}
