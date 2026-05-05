import logging
from app.core.strategy_generator import generate_all_variants, build_strategy_id, TEMPLATES
from app.core.indicators import signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb
from app.core.backtester import run_backtest
from app.core.ranker import compute_score
from app.core.market_data import fetch_ohlcv
from app.db.supabase_client import get_supabase
from app.config import settings

logger = logging.getLogger("synthtrade.pipeline")

SIGNAL_MAP = {
    "trend_ema": lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]),
    "mean_reversion_rsi": lambda df, p: signal_rsi_reversion(
        df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]
    ),
    "breakout_bb": lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]),
}


def build_evaluator():
    from app.ai.model_client import ModelClient
    from app.ai.evaluator import Evaluator
    from app.ai.cache import EvalCache
    client = ModelClient(
        api_key=settings.AI_API_KEY,
        api_base_url=settings.AI_API_BASE_URL,
        cascade_models=settings.ai_cascade_models_list,
        fallback_model=settings.AI_FALLBACK_MODEL,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=settings.AI_MAX_RETRIES,
        backoff_base=settings.AI_BACKOFF_BASE,
    )
    cache = EvalCache(ttl_minutes=settings.AI_EVAL_CACHE_TTL_MINUTES)
    return Evaluator(model_client=client, cache=cache)


async def run_pipeline(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
    days: int = 180,
    ai_eval: bool = True,
) -> int:
    db = get_supabase()
    saved = 0
    saved_strategies = []
    ohlcv_cache: dict[tuple, object] = {}

    for strategy in generate_all_variants(pairs=pairs, timeframes=timeframes):
        try:
            cache_key = (strategy.pair, strategy.timeframe)
            if cache_key not in ohlcv_cache:
                ohlcv_cache[cache_key] = fetch_ohlcv(strategy.pair, strategy.timeframe, days=days)
            ohlcv = ohlcv_cache[cache_key]

            signal_fn = lambda df, p=strategy.params, t=strategy.template: SIGNAL_MAP[t](df, p)
            result = run_backtest(ohlcv, signal_fn)
            score = compute_score(result)

            if score is None:
                continue

            strategy_id = build_strategy_id(strategy)
            row = {
                "id": strategy_id,
                "title": f"{strategy.template} {strategy.pair} {strategy.timeframe}",
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
            }
            db.table("strategies").upsert(row).execute()
            saved_strategies.append(row)
            saved += 1

        except Exception as e:
            logger.warning(f"Strategia {strategy} saltata: {e}")
            continue

    # Passo AI Evaluator sulle top-N strategie
    if ai_eval and saved_strategies:
        top_n = settings.PIPELINE_AI_EVAL_TOP_N
        top = sorted(saved_strategies, key=lambda s: s["score"], reverse=True)[:top_n]
        try:
            evaluator = build_evaluator()
            # Usa l'ohlcv del primo pair/timeframe disponibile
            first_key = next(iter(ohlcv_cache))
            ohlcv = ohlcv_cache[first_key]
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
        except Exception as e:
            logger.error(f"AI eval step failed (pipeline continues): {e}")

    logger.info(f"Pipeline completata: {saved} strategie salvate")
    return saved
