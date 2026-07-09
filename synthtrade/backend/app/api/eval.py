from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from app.dependencies import get_current_user
from app.ai.cache import EvalCache
from app.config import settings
from app.execution.exchange_factory import build_exchange_adapter
from app.services.market_data_service import MarketDataService
import logging

router = APIRouter(prefix="/strategies", tags=["eval"])
logger = logging.getLogger(__name__)


def build_evaluator():
    from app.ai.evaluator import Evaluator
    from app.ai.cache import EvalCache
    from app.services.llm_model_service import LLMModelService
    from app.config import settings

    client = LLMModelService().create_model_client()
    cache = EvalCache(ttl_minutes=settings.AI_EVAL_CACHE_TTL_MINUTES)
    return Evaluator(model_client=client, cache=cache)


@router.get("/{strategy_id}/eval")
def get_eval(strategy_id: str, background_tasks: BackgroundTasks,
             _: str = Depends(get_current_user)):
    cache = EvalCache(ttl_minutes=settings.AI_EVAL_CACHE_TTL_MINUTES)
    cached = cache.get_cached_eval(strategy_id)
    if cached:
        return {
            "strategy_id": cached.strategy_id,
            "score": cached.score,
            "verdict": cached.verdict,
            "reasoning": cached.reasoning,
            "confidence": cached.confidence,
            "model_used": cached.model_used,
            "evaluated_at": cached.evaluated_at.isoformat(),
        }
    return JSONResponse(status_code=202,
                        content={"message": "Evaluation queued", "strategy_id": strategy_id})


@router.post("/{strategy_id}/eval/refresh")
def refresh_eval(strategy_id: str, background_tasks: BackgroundTasks,
                 _: str = Depends(get_current_user)):
    background_tasks.add_task(_run_eval_background, strategy_id)
    return JSONResponse(status_code=202,
                        content={"message": "Refresh queued", "strategy_id": strategy_id})


async def _run_eval_background(strategy_id: str) -> None:
    from app.dependencies import get_market_data_service
    from app.db.supabase_client import get_supabase
    from app.db.repositories.ohlcv_repository import OhlcvRepository
    from app.config import settings

    try:
        db = get_supabase()
        res = db.table("strategies").select("*").eq("id", strategy_id).execute()
        if not res.data:
            return
        strategy = res.data[0]
        
        # Setup temporary dependencies for service
        repo = OhlcvRepository(db)
        exchange = build_exchange_adapter()
        md_service = MarketDataService(repo, exchange)
        
        ohlcv = md_service.get_ohlcv(strategy["pair"], strategy["timeframe"])
        evaluator = build_evaluator()
        await evaluator.evaluate_strategy(strategy, ohlcv)
    except Exception as e:
        logger.error(f"Background eval failed for {strategy_id}: {e}")
