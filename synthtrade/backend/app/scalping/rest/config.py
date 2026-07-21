"""Config and risk config endpoints.

Extracted from rest/session.py (TASK-1166.E).
"""
import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter

from app.scalping._state import _execution_state
from app.scalping.config_loader import get_scalping_config
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config")
async def get_scalping_config_endpoint():
    cfg = get_scalping_config()
    return {"config": cfg._config, "source": "env+db_override"}

@router.post("/config/reload")
async def reload_scalping_config():
    get_scalping_config().reload()
    return {"status": "reloaded"}

@router.post("/config/{key}")
async def update_scalping_config(key: str, value: str):
    db = get_supabase()
    db.table("scalping_runtime_config").update({
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("key", key).execute()
    get_scalping_config().reload()
    return {"key": key, "value": value, "status": "updated"}


@router.get("/risk/config")
async def get_risk_config() -> Dict:
    try:
        supabase = get_supabase()
        response = supabase.table("scalping_risk_config").select("*").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            db_config = response.data[0]
            # Exclude id, updated_at from the active memory representation
            clean_config = {k: v for k, v in db_config.items() if k not in ["id", "updated_at"]}
            _execution_state["risk_config"] = clean_config
            return clean_config
    except Exception as e:
        logger.error(f"Error fetching risk config from DB: {e}")
    # Fallback to memory
    return _execution_state.get("risk_config", {})

@router.post("/risk/config")
async def update_risk_config(config: Dict) -> Dict:
    # Exclude position_size if present (managed via trade_value instead)
    clean_cfg = {k: v for k, v in config.items() if k != "position_size"}
    _execution_state["risk_config"] = clean_cfg
    
    # Persist to Supabase
    try:
        supabase = get_supabase()
        db_payload = {
            "id": 1,
            "max_daily_loss": clean_cfg.get("max_daily_loss", 50),
            "max_drawdown": clean_cfg.get("max_drawdown", 10),
            "leverage": clean_cfg.get("leverage", 10),
            "stop_loss_pct": clean_cfg.get("stop_loss_pct", 1.05),
            "take_profit_pct": clean_cfg.get("take_profit_pct", 1.55),
        }
        supabase.table("scalping_risk_config").upsert(db_payload).execute()
        logger.info("Persisted risk config to Supabase")
    except Exception as e:
        logger.error(f"Error persisting risk config to DB: {e}")
        
    return clean_cfg
