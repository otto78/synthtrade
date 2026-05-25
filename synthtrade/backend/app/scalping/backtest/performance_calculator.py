"""PerformanceCalculator — calcolo metriche di performance per backtest (TASK-808).

Calcola win rate, drawdown, Sharpe ratio, profit factor, avg win/loss,
consecutive losses e correlazione signal_score → trade outcome.
"""

import math
from decimal import Decimal
from statistics import mean, stdev
from typing import Dict, List, Optional

from app.scalping.models.backtest import BacktestResult, BacktestMetric, SimulatedTrade


class PerformanceCalculator:
    """Calcolatore di metriche di performance per backtest.

    Uso:
        calculator = PerformanceCalculator()
        metrics = calculator.calculate(result)
    """

    def calculate(self, result: BacktestResult) -> Dict[str, float]:
        """Calcola tutte le metriche dal risultato del backtest.

        Args:
            result: BacktestResult con trades ed equity curve.

        Returns:
            Dict con metriche calcolate.
        """
        closed_trades = [t for t in result.trades if t.is_closed]

        if not closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "consecutive_losses": 0,
                "avg_trade_duration_hours": 0.0,
                "signal_correlation": 0.0,
            }

        win_rate = self._win_rate(closed_trades)
        total_pnl, total_pnl_pct = self._total_pnl(closed_trades, result.config.initial_capital)
        profit_factor = self._profit_factor(closed_trades)
        avg_win, avg_loss = self._avg_win_loss(closed_trades)
        max_drawdown = self._max_drawdown(result.equity_curve)
        sharpe = self._sharpe_ratio(result.equity_curve)
        consecutive_losses = self._consecutive_losses(closed_trades)
        avg_duration = self._avg_trade_duration(closed_trades)
        signal_corr = self._signal_correlation(closed_trades)

        metrics = {
            "total_trades": len(closed_trades),
            "winning_trades": len([t for t in closed_trades if t.pnl is not None and t.pnl > 0]),
            "losing_trades": len([t for t in closed_trades if t.pnl is not None and t.pnl <= 0]),
            "win_rate": round(win_rate, 4),
            "total_pnl": round(float(total_pnl), 2),
            "total_pnl_pct": round(float(total_pnl_pct), 4),
            "profit_factor": round(profit_factor, 4),
            "avg_win": round(float(avg_win), 2),
            "avg_loss": round(float(avg_loss), 2),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe, 4),
            "consecutive_losses": consecutive_losses,
            "avg_trade_duration_hours": round(avg_duration, 4),
            "signal_correlation": round(signal_corr, 4),
        }

        result.metrics = metrics
        result.metrics_detail = self._metrics_detail(metrics)
        return metrics

    def calculate_correlation(self, result: BacktestResult) -> Dict[str, float]:
        """Calcola correlazione tra signal_score e trade outcome.

        Returns:
            Dict con coefficienti di correlazione.
        """
        pairs = [
            (t.signal_score, t.pnl)
            for t in result.trades
            if t.is_closed and t.signal_score is not None and t.pnl is not None
        ]

        if len(pairs) < 3:
            return {"spearman": 0.0, "pearson": 0.0}

        scores = [float(s) for s, _ in pairs]
        pnls_vals = [float(p) for _, p in pairs]

        pearson = self._pearson_correlation(scores, pnls_vals)
        spearman = self._spearman_correlation(scores, pnls_vals)

        correlation = {"pearson": round(pearson, 4), "spearman": round(spearman, 4)}
        result.correlation_data = correlation
        return correlation

    # ─────────────────────────────
    # Metodi privati
    # ─────────────────────────────

    @staticmethod
    def _win_rate(trades: List[SimulatedTrade]) -> float:
        """Win rate come frazione 0..1."""
        winning = len([t for t in trades if t.pnl is not None and t.pnl > 0])
        return winning / len(trades) if trades else 0.0

    @staticmethod
    def _total_pnl(trades: List[SimulatedTrade], initial_capital: Decimal):
        """P&L totale e percentuale."""
        total = sum((float(t.pnl) if t.pnl is not None else 0.0) for t in trades)
        pct = (total / float(initial_capital)) * 100 if initial_capital > 0 else 0.0
        return Decimal(str(total)), Decimal(str(pct))

    @staticmethod
    def _profit_factor(trades: List[SimulatedTrade]) -> float:
        """Profit factor: somma win / somma loss (valore assoluto)."""
        gross_win = sum(float(t.pnl) for t in trades if t.pnl is not None and t.pnl > 0)
        gross_loss = abs(sum(float(t.pnl) for t in trades if t.pnl is not None and t.pnl < 0))
        return gross_win / gross_loss if gross_loss > 0 else (gross_win if gross_win > 0 else 0.0)

    @staticmethod
    def _avg_win_loss(trades: List[SimulatedTrade]):
        """Media win e media loss."""
        wins = [float(t.pnl) for t in trades if t.pnl is not None and t.pnl > 0]
        losses = [float(t.pnl) for t in trades if t.pnl is not None and t.pnl < 0]
        avg_win = mean(wins) if wins else 0.0
        avg_loss = mean(losses) if losses else 0.0
        return avg_win, avg_loss

    @staticmethod
    def _max_drawdown(equity_curve: List[Dict]) -> float:
        """Maximum drawdown dalla equity curve."""
        if not equity_curve:
            return 0.0

        peak = float("-inf")
        max_dd = 0.0

        for point in equity_curve:
            equity = point.get("equity", 0)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    @staticmethod
    def _sharpe_ratio(equity_curve: List[Dict], risk_free_rate: float = 0.02) -> float:
        """Sharpe ratio annualizzato basato su equity curve.

        Usa rendimenti periodici (log returns).
        """
        if len(equity_curve) < 3:
            return 0.0

        equities = [p.get("equity", 0) for p in equity_curve]
        returns = []

        for i in range(1, len(equities)):
            prev = equities[i - 1]
            curr = equities[i]
            if prev > 0:
                ret = (curr - prev) / prev
                returns.append(ret)

        if len(returns) < 2:
            return 0.0

        avg_return = mean(returns)
        std_return = stdev(returns)

        if std_return == 0:
            return 0.0

        # Annualizza (assumiamo periodi orari, ~8760 ore/anno)
        periods_per_year = 8760
        excess_return = avg_return - (risk_free_rate / periods_per_year)
        sharpe = (excess_return / std_return) * math.sqrt(periods_per_year)
        return sharpe

    @staticmethod
    def _consecutive_losses(trades: List[SimulatedTrade]) -> int:
        """Massimo numero di perdite consecutive."""
        max_losses = 0
        current_losses = 0

        for t in trades:
            if t.pnl is not None and t.pnl < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0

        return max_losses

    @staticmethod
    def _avg_trade_duration(trades: List[SimulatedTrade]) -> float:
        """Durata media dei trade in ore."""
        durations = []
        for t in trades:
            if t.exit_time and t.entry_time:
                delta = t.exit_time - t.entry_time
                durations.append(delta.total_seconds() / 3600)

        return mean(durations) if durations else 0.0

    @staticmethod
    def _signal_correlation(trades: List[SimulatedTrade]) -> float:
        """Correlazione Pearson tra signal_score e P&L."""
        pairs = [(t.signal_score, t.pnl) for t in trades if t.signal_score is not None and t.pnl is not None]
        if len(pairs) < 3:
            return 0.0
        scores = [float(s) for s, _ in pairs]
        pnls = [float(p) for _, p in pairs]
        return PerformanceCalculator._pearson_correlation(scores, pnls)

    @staticmethod
    def _pearson_correlation(x: List[float], y: List[float]) -> float:
        """Correlazione Pearson tra due liste."""
        if len(x) < 3 or len(y) < 3:
            return 0.0

        n = len(x)
        x_mean = mean(x)
        y_mean = mean(y)

        num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        den_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))
        den_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))

        if den_x == 0 or den_y == 0:
            return 0.0

        return num / (den_x * den_y)

    @staticmethod
    def _spearman_correlation(x: List[float], y: List[float]) -> float:
        """Correlazione Spearman (basata su ranghi)."""
        if len(x) < 3 or len(y) < 3:
            return 0.0

        def rank(values: List[float]) -> List[float]:
            sorted_vals = sorted(values)
            return [float(sorted_vals.index(v) + 1) for v in values]

        x_rank = rank(x)
        y_rank = rank(y)

        return PerformanceCalculator._pearson_correlation(x_rank, y_rank)

    @staticmethod
    def _metrics_detail(metrics: Dict[str, float]) -> List[BacktestMetric]:
        """Converte metriche in lista di BacktestMetric per report."""
        return [
            BacktestMetric(label="Total Trades", value=metrics.get("total_trades", 0), unit="trades"),
            BacktestMetric(label="Win Rate", value=metrics.get("win_rate", 0) * 100, unit="%", higher_is_better=True),
            BacktestMetric(label="Total PnL", value=metrics.get("total_pnl", 0), unit="USDT", higher_is_better=True),
            BacktestMetric(label="Total PnL %", value=metrics.get("total_pnl_pct", 0), unit="%", higher_is_better=True),
            BacktestMetric(label="Profit Factor", value=metrics.get("profit_factor", 0), unit="x", higher_is_better=True),
            BacktestMetric(label="Max Drawdown", value=metrics.get("max_drawdown", 0) * 100, unit="%", higher_is_better=False),
            BacktestMetric(label="Sharpe Ratio", value=metrics.get("sharpe_ratio", 0), unit="", higher_is_better=True),
            BacktestMetric(label="Consecutive Losses", value=metrics.get("consecutive_losses", 0), unit="trades", higher_is_better=False),
            BacktestMetric(label="Avg Win", value=metrics.get("avg_win", 0), unit="USDT", higher_is_better=True),
            BacktestMetric(label="Avg Loss", value=metrics.get("avg_loss", 0), unit="USDT", higher_is_better=False),
            BacktestMetric(label="Signal Correlation", value=metrics.get("signal_correlation", 0), unit="", higher_is_better=True),
        ]