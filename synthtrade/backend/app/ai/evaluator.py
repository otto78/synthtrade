import asyncio
import logging
import pandas as pd
from app.ai.schemas import EvalResult
from app.ai.context_builder import build_market_context
from app.ai.prompt_builder import build_prompt, build_system_prompt
from app.ai.eval_parser import parse_eval_result, EvalParseError
from app.ai.model_client import ModelClient, AllModelsUnavailableError
from app.ai.cache import EvalCache


class Evaluator:
    def __init__(self, model_client: ModelClient, cache: EvalCache, logger=None):
        self.model_client = model_client
        self.cache = cache
        self.logger = logger or logging.getLogger(__name__)

    async def evaluate_strategy(self, strategy: dict,
                                 ohlcv: pd.DataFrame) -> EvalResult | None:
        strategy_id = strategy["id"]

        cached = self.cache.get_cached_eval(strategy_id)
        if cached:
            return cached

        try:
            market_ctx = build_market_context(
                ohlcv, symbol=strategy["pair"], timeframe=strategy["timeframe"])
        except Exception as e:
            self.logger.error(f"Context build failed for {strategy_id}: {e}")
            return None

        from app.ai.schemas import StrategyContext, EvalPromptInput
        bt = strategy.get("backtest") or {}
        strategy_ctx = StrategyContext(
            strategy_id=strategy_id,
            title=strategy.get("title", ""),
            template=strategy.get("template", ""),
            params=strategy.get("params", {}),
            pnl_pct=bt.get("pnl_pct", 0.0),
            win_rate=bt.get("win_rate", 0.0),
            sharpe=bt.get("sharpe", 0.0),
            max_drawdown_pct=bt.get("max_drawdown_pct", 0.0),
            num_trades=bt.get("num_trades", 0),
            score=strategy.get("score", 0.0),
        )
        prompt_input = EvalPromptInput(market=market_ctx, strategy=strategy_ctx)
        system = build_system_prompt()
        user = build_prompt(prompt_input)

        try:
            response = await self.model_client.call_with_fallback(system, user)
        except AllModelsUnavailableError as e:
            self.logger.error(f"All models unavailable for {strategy_id}: {e}")
            return None

        try:
            result = parse_eval_result(response.content, strategy_id, response.model)
            result.tokens_used = response.tokens_used
        except EvalParseError as e:
            self.logger.error(f"EvalParseError for {strategy_id}: {e}")
            return None

        self.cache.save_eval(result)
        return result

    async def evaluate_all(self, strategies: list[dict], ohlcv: pd.DataFrame,
                           max_concurrent: int = 3) -> list[EvalResult | None]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _eval(s):
            async with semaphore:
                return await self.evaluate_strategy(s, ohlcv)

        return list(await asyncio.gather(*[_eval(s) for s in strategies]))
