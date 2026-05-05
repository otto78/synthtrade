import logging
from app.core.strategy_generator import generate_all_variants, build_strategy_id, TEMPLATES
from app.core.indicators import signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb
from app.core.backtester import run_backtest
from app.core.ranker import compute_score
from app.core.market_data import fetch_ohlcv
from app.db.supabase_client import get_supabase

logger = logging.getLogger("synthtrade.pipeline")

SIGNAL_MAP = {
    "trend_ema": lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]),
    "mean_reversion_rsi": lambda df, p: signal_rsi_reversion(
        df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]
    ),
    "breakout_bb": lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]),
}


def run_pipeline(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
    days: int = 180,
) -> int:
    db = get_supabase()
    saved = 0

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
            saved += 1

        except Exception as e:
            logger.warning(f"Strategia {strategy} saltata: {e}")
            continue

    logger.info(f"Pipeline completata: {saved} strategie salvate")
    return saved
