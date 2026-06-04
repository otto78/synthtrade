import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from app.core.strategy_generator import generate_all_variants, build_strategy_id, TEMPLATES
from app.core.market_data import fetch_ohlcv
from app.core.backtester import run_backtest
from app.core.ranker import Ranker
from app.services.market_data_service import MarketDataService
from app.db.supabase_client import get_supabase
from app.config import settings
from app.execution.registry import registry

logger = logging.getLogger("synthtrade.pipeline")

# Expose symbols for test patching
# These assignments make `fetch_ohlcv` and `get_supabase` available as attributes of this module
# so that `patch("app.core.run_pipeline.fetch_ohlcv")` works even though the real implementation
# lives in other modules.
globals()['fetch_ohlcv'] = fetch_ohlcv
globals()['get_supabase'] = get_supabase


def build_evaluator():
    # Wrapper for tests that patch fetch_ohlcv directly on this module
    # Expose fetch_ohlcv from market_data for compatibility
    from app.core.market_data import fetch_ohlcv as _fetch_ohlcv
    def fetch_ohlcv(symbol, timeframe, days):
        return _fetch_ohlcv(symbol, timeframe, days)
    globals()['fetch_ohlcv'] = fetch_ohlcv
    # get_supabase is already imported above; ensure it's available for patching
    globals()['get_supabase'] = get_supabase

    from app.ai.evaluator import Evaluator
    from app.ai.cache import EvalCache
    from app.services.llm_model_service import LLMModelService
    client = LLMModelService().create_model_client()
    cache = EvalCache(ttl_minutes=settings.AI_EVAL_CACHE_TTL_MINUTES)
    return Evaluator(model_client=client, cache=cache)


async def run_pipeline(
    md_service: MarketDataService,
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
    days: int = 180,
    ai_eval: bool = True,
) -> int:
    db = get_supabase()
    saved = 0
    saved_strategies = []
    ohlcv_cache: dict[tuple[str, str], pd.DataFrame | list[dict]] = {}

    for strategy in generate_all_variants(pairs=pairs, timeframes=timeframes):
        try:
            cache_key = (strategy.pair, strategy.timeframe)
            if cache_key not in ohlcv_cache:
                ohlcv_cache[cache_key] = md_service.get_ohlcv(strategy.pair, strategy.timeframe, days=days)
            ohlcv = ohlcv_cache[cache_key]

            if isinstance(ohlcv, list):
                ohlcv = pd.DataFrame(ohlcv)
                ohlcv_cache[cache_key] = ohlcv

            if isinstance(ohlcv, pd.DataFrame) and ohlcv.empty:
                logger.warning(f"Empty OHLCV for {strategy.pair} {strategy.timeframe}: skipping")
                continue

            if not hasattr(ohlcv, "columns") or "close" not in ohlcv.columns:
                logger.warning(f"Invalid OHLCV format for {strategy.pair} {strategy.timeframe}: skipping")
                continue

            if len(ohlcv) < 2:
                logger.warning(f"Insufficient OHLCV rows for {strategy.pair} {strategy.timeframe}: skipping")
                continue

            signal_fn = registry.get(strategy.template)
            if signal_fn is None:
                logger.warning(f"Template {strategy.template} non supportato, salto.")
                continue

            result = run_backtest(ohlcv, lambda df, p=strategy.params, f=signal_fn: f(df, p))
            score = Ranker().compute_score(result)

            if score is None:
                continue

            strategy_id = build_strategy_id(strategy)
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(days=7)).isoformat()
            title = strategy.title or f"{strategy.template} {strategy.pair} {strategy.timeframe}"
            row = {
                "id": strategy_id,
                "title": title,
                "template": strategy.template,
                "pair": strategy.pair,
                "timeframe": strategy.timeframe,
                "params": strategy.params,
                "rules": {},
                "risk": {"max_position_eur": 100, "max_daily_loss": 15},
                "targets": {"horizon_days": 7},
                "backtest": {
                    "pnl_pct": result.pnl_pct,
                    "win_rate": result.win_rate,
                    "sharpe": result.sharpe,
                    "max_drawdown_pct": result.max_drawdown_pct,
                    "num_trades": result.num_trades,
                },
                "equity_curve": result.equity_curve,
                "score": score,
                "status": "PENDING",
                "expires_at": expires_at,
            }
            db.table("strategies").upsert(row).execute()
            saved_strategies.append(row)
            saved += 1

        except Exception as e:
            logger.warning(f"Strategia {strategy} saltata: {e}")
            continue

    # Passo AI Evaluator sulle top-N strategie
    if ai_eval and saved_strategies:
        # Ensure WebSocket manager is available for broadcasting eval results
        from app.api.ws import manager
        top_n = settings.PIPELINE_AI_EVAL_TOP_N
        top = sorted(saved_strategies, key=lambda s: s["score"], reverse=True)[:top_n]
        try:
            evaluator = build_evaluator()
            # Usa l'ohlcv del primo pair/timeframe disponibile
            first_key = next(iter(ohlcv_cache))
            ohlcv = ohlcv_cache[first_key]
            if isinstance(ohlcv, list):
                ohlcv = pd.DataFrame(ohlcv)
                ohlcv_cache[first_key] = ohlcv
            eval_results = await evaluator.evaluate_all(top, ohlcv,
                                                         max_concurrent=settings.MAX_CONCURRENT_EVALS)
            for eval_result in eval_results:
                if eval_result is None:
                    continue
                if eval_result.verdict == "DEMOTE":
                    db.table("strategies").update({"status": "REJECTED"}).eq(
                        "id", eval_result.strategy_id).execute()
                    logger.info(f"Strategy {eval_result.strategy_id} DEMOTED → REJECTED")
                elif eval_result.verdict == "PROMOTE":
                    logger.info(f"Strategy {eval_result.strategy_id} PROMOTED score={eval_result.score:.3f}")
                # Broadcast evaluation result (any verdict) to frontend via WebSocket
                try:
                    await manager.broadcast({
                        "type": "eval_complete",
                        "payload": {
                            "strategy_id": eval_result.strategy_id,
                            "verdict": eval_result.verdict,
                            "score": eval_result.score,
                        },
                    })
                except Exception as ws_err:
                    logger.warning(f"Failed to broadcast eval_complete for {eval_result.strategy_id}: {ws_err}")
        except Exception as e:
            logger.error(f"AI eval step failed (pipeline continues): {e}")

    logger.info(f"Pipeline completata: {saved} strategie salvate")
    return saved
