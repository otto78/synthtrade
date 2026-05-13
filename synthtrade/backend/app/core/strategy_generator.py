import asyncio
import logging
from itertools import product
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Generator, Tuple
from app.execution.schemas import StrategyRequest
from app.ai.request_enricher import enrich_request_with_ai
from app.core.market_data import fetch_ohlcv
from app.core.backtester import run_backtest, BacktestResult
from app.core.ranker import compute_score, RankConfig
from app.core.indicators import signal_ema_crossover, signal_rsi_reversion, signal_breakout_bb

logger = logging.getLogger("synthtrade.generator")

QUALITY_EMPTY_MESSAGE = (
    "Nessuna strategia ha superato i criteri di qualità sui dati storici "
    "(Trades >= 15, Sharpe >= 0, Drawdown < 40%, P&L > 0% su 60 giorni). "
    "Prova con un orizzonte temporale più lungo o un livello di rischio diverso."
)

MARKET_DATA_EMPTY_MESSAGE = (
    "Impossibile scaricare dati di mercato per i simboli indicati. "
    "Verifica il formato (es. BTC/USDT o BTCUSDT) e la connessione di rete."
)


def normalize_trading_pair(symbol: str) -> str:
    """
    Converte chip tipo BTCUSDT nel formato ccxt/Binance BTC/USDT.
    """
    s = symbol.strip().upper()
    if "/" in s:
        return s
    quotes = ("USDT", "USDC", "BUSD", "EUR", "FDUSD", "BTC", "ETH", "BNB")
    for quote in quotes:
        if len(s) > len(quote) and s.endswith(quote):
            base = s[: -len(quote)]
            if base:
                return f"{base}/{quote}"
    return s


SIGNAL_MAP = {
    "trend_ema": lambda df, p: signal_ema_crossover(df, p["ema_fast"], p["ema_slow"]),
    "mean_reversion_rsi": lambda df, p: signal_rsi_reversion(
        df, p["rsi_period"], p["rsi_oversold"], p["rsi_overbought"]
    ),
    "breakout_bb": lambda df, p: signal_breakout_bb(df, p["bb_period"], p["bb_std"]),
}

TEMPLATES: dict[str, dict] = {
    "trend_ema": {
        "title": "Trend Following EMA",
        "description": "Segue il trend utilizzando incroci di medie mobili esponenziali.",
        "duration_days": 30,
        "risk_level": "medium",
        "params": {
            "ema_fast":    [10, 20],
            "ema_slow":    [50, 100],
            "stop_loss":   [0.02, 0.03],
            "take_profit": [0.05, 0.08],
        }
    },
    "mean_reversion_rsi": {
        "title": "Mean Reversion RSI",
        "description": "Sfrutta l'ipercomprato/ipervenduto per ritorni verso la media.",
        "duration_days": 15,
        "risk_level": "low",
        "params": {
            "rsi_period":     [14],
            "rsi_oversold":   [25, 30],
            "rsi_overbought": [70, 75],
            "stop_loss":      [0.02],
            "take_profit":    [0.04, 0.06],
        }
    },
    "breakout_bb": {
        "title": "Bollinger Breakout",
        "description": "Entra a mercato sulle rotture delle bande di Bollinger con alta volatilità.",
        "duration_days": 7,
        "risk_level": "high",
        "params": {
            "bb_period":   [20],
            "bb_std":      [2.0, 2.5],
            "stop_loss":   [0.03],
            "take_profit": [0.07, 0.10],
        }
    },
}


@dataclass(frozen=True)
class StrategyParams:
    template: str
    pair: str
    timeframe: str
    params: dict
    budget_eur: float = 100.0
    title: Optional[str] = None
    description: Optional[str] = None
    score: float = 0.0                # da compute_score() — deterministico
    estimated_profit_pct: float = 0.0 # da result.pnl_pct — reale
    estimated_profit_eur: float = 0.0 # budget * pnl_pct / 100 — reale
    backtest_pnl: float = 0.0         # result.pnl_pct
    backtest_win_rate: float = 0.0    # result.win_rate
    backtest_sharpe: float = 0.0      # result.sharpe
    backtest_drawdown: float = 0.0    # result.max_drawdown_pct
    backtest_trades: int = 0          # result.num_trades
    data_source: str = ""             # es. "binance_1h_90d"
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    custom_name: Optional[str] = None

    def __hash__(self):
        return hash((self.template, self.pair, self.timeframe, tuple(sorted(self.params.items())), self.budget_eur))

    def __post_init__(self):
        # Garantisce budget non nullo
        if self.budget_eur is None or self.budget_eur <= 0:
            object.__setattr__(self, 'budget_eur', 100.0)
        # Garantisce titolo e descrizione
        if not self.title and self.template in TEMPLATES:
            object.__setattr__(self, 'title', f"{TEMPLATES[self.template]['title']} ({self.pair})")
        if not self.description and self.template in TEMPLATES:
            object.__setattr__(self, 'description', TEMPLATES[self.template]['description'])


async def generate_for_request(req: StrategyRequest) -> Tuple[List[StrategyParams], Optional[str]]:
    """
    TASK-FIX-003/004: Generatore con backtest reale su dati storici Binance.
    Nessun random.uniform(), nessun nome casuale.
    """
    req = await enrich_request_with_ai(req)
    filtered_templates = _filter_templates_by_constraints(req)

    if req.symbols:
        pairs = [normalize_trading_pair(p) for p in req.symbols]
    else:
        # Default: top marketcap crypto per massimizzare probabilità strategie valide
        pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
    # Timeframe 1h = buon bilanciamento segnali/rumore; 4h = trend più ampi
    timeframes = ["1h", "4h"]
    # 60 giorni = periodo sufficiente per significatività statistica senza includere
    # trend troppo vecchi che potrebbero non essere più validi
    lookback_days = 60

    # TASK-FIX-003: Cache OHLCV — una sola chiamata per (pair, timeframe)
    ohlcv_cache: dict[tuple, object] = {}
    for pair in pairs:
        for tf in timeframes:
            key = (pair, tf)
            try:
                ohlcv_cache[key] = await asyncio.to_thread(
                    fetch_ohlcv, pair, tf, lookback_days
                )
                n_candles = len(ohlcv_cache[key])
                logger.info(f"OHLCV: {pair} {tf} — {n_candles} candele")
            except Exception as e:
                logger.warning(f"OHLCV fetch fallito {pair}/{tf}: {e}")

    fetch_had_data = any(
        df is not None and not (hasattr(df, "empty") and df.empty)
        for df in ohlcv_cache.values()
    )

    results: List[StrategyParams] = []
    now = datetime.now(timezone.utc)

    # TASK-FIX-004: Loop backtest reale (sostituisce random)
    for template_name in filtered_templates:
        template_data = TEMPLATES[template_name]
        param_grid = template_data["params"]
        keys = list(param_grid.keys())
        combos = list(product(*param_grid.values()))

        for pair, tf, combo in product(pairs, timeframes, combos):
            ohlcv = ohlcv_cache.get((pair, tf))
            if ohlcv is None or (hasattr(ohlcv, 'empty') and ohlcv.empty):
                continue

            params_dict = dict(zip(keys, combo))

            try:
                signal_fn = lambda df, t=template_name, p=params_dict: SIGNAL_MAP[t](df, p)
                bt = run_backtest(ohlcv, signal_fn)
                score = compute_score(bt)
                if score is None:
                    continue  # Non supera soglie qualità — scartata

                budget = float(req.budget_eur) if req.budget_eur > 0 else 100.0
                title = f"{template_data['title']} — {pair} {tf}"
                custom_name = req.custom_name or title
                data_source = f"binance_{tf}_{lookback_days}d"

                variant = StrategyParams(
                    template=template_name,
                    pair=pair,
                    timeframe=tf,
                    params=params_dict,
                    budget_eur=budget,
                    title=title,
                    description=template_data["description"],
                    score=score,
                    estimated_profit_pct=round(bt.pnl_pct, 4),
                    estimated_profit_eur=round(budget * bt.pnl_pct / 100, 4),
                    backtest_pnl=bt.pnl_pct,
                    backtest_win_rate=bt.win_rate,
                    backtest_sharpe=bt.sharpe,
                    backtest_drawdown=bt.max_drawdown_pct,
                    backtest_trades=bt.num_trades,
                    data_source=data_source,
                    custom_name=custom_name,
                    created_at=now.isoformat(),
                    expires_at=(now + timedelta(days=7)).isoformat(),
                )
                results.append(variant)
            except Exception as e:
                logger.warning(f"Backtest fallito {template_name}/{pair}/{tf}: {e}")

    logger.info(f"Generator: {len(results)} strategie superano i filtri")
    out = sorted(results, key=lambda x: x.score, reverse=True)[: req.max_strategies]
    if not out:
        hint = MARKET_DATA_EMPTY_MESSAGE if not fetch_had_data else QUALITY_EMPTY_MESSAGE
        return [], hint
    return out, None


def generate_all_variants(
    pairs: list[str] = ["BTC/USDT"],
    timeframes: list[str] = ["5m", "15m"],
) -> Generator[StrategyParams, None, None]:
    """Prodotto cartesiano: tipicamente 200–800 strategie candidate."""
    for template_name, template_data in TEMPLATES.items():
        param_grid = template_data["params"]
        keys = list(param_grid.keys())
        for pair, timeframe, combo in product(pairs, timeframes, product(*param_grid.values())):
            yield StrategyParams(
                template=template_name,
                pair=pair,
                timeframe=timeframe,
                params=dict(zip(keys, combo)),
                title=f"{template_data['title']} ({pair})",
                description=template_data["description"]
            )


def build_strategy_id(s: StrategyParams) -> str:
    """Genera un ID deterministico basato sui parametri."""
    import hashlib
    import json
    payload = f"{s.template}:{s.pair}:{s.timeframe}:{json.dumps(s.params, sort_keys=True)}"
    return hashlib.md5(payload.encode()).hexdigest()[:10]


def _filter_templates_by_constraints(req: StrategyRequest) -> List[str]:
    valid_templates = []
    for name, data in TEMPLATES.items():
        # Durata ± 50% per essere più flessibili nella generazione
        dur = data.get("duration_days", 30)
        if not (req.duration_days * 0.5 <= dur <= req.duration_days * 1.5):
            continue

        # Rischio
        if req.risk_level == "low" and data.get("risk_level") == "high":
            continue

        valid_templates.append(name)

    # Se nessun template soddisfa i vincoli rigidi, restituiamo quello più vicino
    if not valid_templates:
        return [list(TEMPLATES.keys())[0]]

    return valid_templates