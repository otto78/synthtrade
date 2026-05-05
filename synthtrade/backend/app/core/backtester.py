import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Callable

FEE_PCT = 0.001    # 0.1% Binance taker
SLIPPAGE = 0.0007  # 0.07% slippage medio


@dataclass
class BacktestResult:
    pnl_pct: float
    win_rate: float
    sharpe: float
    max_drawdown_pct: float
    num_trades: int
    equity_curve: list[float] = field(default_factory=list)


def run_backtest(
    ohlcv: pd.DataFrame,
    signal_fn: Callable[[pd.DataFrame], pd.Series],
    initial_capital: float = 1000.0,
) -> BacktestResult:
    signals = signal_fn(ohlcv)
    capital, position, entry_price = initial_capital, 0.0, 0.0
    equity_curve = [initial_capital]
    trades: list[float] = []

    for i in range(1, len(ohlcv)):
        price = ohlcv["close"].iloc[i]
        signal = signals.iloc[i]

        if signal == 1 and position == 0 and capital > 0:
            exec_price = price * (1 + SLIPPAGE)
            position = capital * (1 - FEE_PCT) / exec_price
            capital = 0.0
            entry_price = exec_price

        elif signal == -1 and position > 0:
            exec_price = price * (1 - SLIPPAGE)
            proceeds = position * exec_price * (1 - FEE_PCT)
            trades.append((exec_price - entry_price) / entry_price)
            capital, position = proceeds, 0.0

        current = capital + position * price
        equity_curve.append(current)

    # Chiudi posizione aperta a fine serie
    if position > 0:
        final_price = ohlcv["close"].iloc[-1] * (1 - SLIPPAGE) * (1 - FEE_PCT)
        proceeds = position * final_price
        trades.append((final_price - entry_price) / entry_price)
        equity_curve[-1] = proceeds
        capital = proceeds
        position = 0.0

    final_equity = equity_curve[-1]
    pnl_pct = (final_equity - initial_capital) / initial_capital * 100

    if not trades:
        pnl_pct = 0.0

    win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0.0

    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = (float(returns.mean() / returns.std()) * np.sqrt(252 * 288)
              if returns.std() > 0 else 0.0)

    eq = pd.Series(equity_curve)
    dd = (eq - eq.cummax()) / eq.cummax()
    max_dd = float(abs(dd.min()) * 100)

    return BacktestResult(
        pnl_pct=round(pnl_pct, 4),
        win_rate=round(win_rate, 4),
        sharpe=round(sharpe, 4),
        max_drawdown_pct=round(max_dd, 4),
        num_trades=len(trades),
        equity_curve=equity_curve,
    )
