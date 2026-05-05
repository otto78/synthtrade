from app.ai.schemas import EvalPromptInput

_SYSTEM_PROMPT = """You are a quantitative analyst AI specializing in crypto trading strategy evaluation.
Your task is to evaluate a trading strategy based on backtest metrics and market context.
You MUST respond with a valid JSON object only, no markdown, no explanation outside JSON.
Required fields: score (float 0-1), verdict (PROMOTE|HOLD|DEMOTE), reasoning (string), confidence (float 0-1)."""

_PROMPT_TEMPLATE = """## Market Context
Symbol: {symbol} | Timeframe: {timeframe} | Regime: {regime}
Price range: {price_min:.0f} – {price_max:.0f} | Last: {price_last:.0f}
Volatility: {volatility_pct:.2f}% | Trend: {trend_pct:+.2f}%

## Strategy: {title}
Template: {template} | Params: {params}
PnL: {pnl_pct:+.2f}% | Win rate: {win_rate:.0%} | Sharpe: {sharpe:.2f}
Max drawdown: {max_drawdown_pct:.2f}% | Trades: {num_trades} | Score: {score:.4f}

## Task
Evaluate this strategy. Respond ONLY with JSON:
{{"score": <0.0-1.0>, "verdict": "<PROMOTE|HOLD|DEMOTE>", "reasoning": "<explanation>", "confidence": <0.0-1.0>}}"""


def build_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_prompt(inp: EvalPromptInput, max_chars: int | None = None) -> str:
    m, s = inp.market, inp.strategy
    prompt = _PROMPT_TEMPLATE.format(
        symbol=m.symbol, timeframe=m.timeframe, regime=m.regime,
        price_min=m.summary.price_min, price_max=m.summary.price_max,
        price_last=m.summary.price_last, volatility_pct=m.summary.volatility_pct,
        trend_pct=m.summary.trend_pct, title=s.title, template=s.template,
        params=s.params, pnl_pct=s.pnl_pct, win_rate=s.win_rate,
        sharpe=s.sharpe, max_drawdown_pct=s.max_drawdown_pct,
        num_trades=s.num_trades, score=s.score,
    )
    if max_chars:
        prompt = prompt[:max_chars]
    return prompt
