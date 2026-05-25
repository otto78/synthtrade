"""ReportGenerator — generazione report JSON per backtest (TASK-808).

Produce un report strutturato con metriche, confronto with/without intelligence,
e riepilogo esecutivo.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.scalping.models.backtest import BacktestConfig, BacktestMetric, BacktestResult
from app.scalping.backtest.performance_calculator import PerformanceCalculator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generatore di report per backtest.

    Uso:
        generator = ReportGenerator()
        report = generator.generate_report(result)
    """

    def __init__(self, calculator: Optional[PerformanceCalculator] = None):
        self._calculator = calculator or PerformanceCalculator()

    def generate_report(
        self,
        result: BacktestResult,
        comparison_result: Optional[BacktestResult] = None,
    ) -> Dict[str, Any]:
        """Genera report JSON completo.

        Args:
            result: Risultato del backtest principale.
            comparison_result: Opzionale, risultato per confronto (es: senza intelligence).

        Returns:
            Dict struttura report.
        """
        if not result.metrics:
            self._calculator.calculate(result)
        if not result.correlation_data:
            self._calculator.calculate_correlation(result)

        report = {
            "report_id": result.id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "config": self._serialize_config(result.config),
            "summary": self._generate_summary(result),
            "metrics": result.metrics,
            "metrics_detail": [m.model_dump() for m in result.metrics_detail],
            "correlation": result.correlation_data,
            "trades": self._serialize_trades(result.trades),
            "equity_curve_preview": self._equity_curve_preview(result.equity_curve),
            "errors": result.errors,
            "duration_seconds": result.duration_seconds,
        }

        # Confronto con/senza intelligence
        if comparison_result:
            if not comparison_result.metrics:
                self._calculator.calculate(comparison_result)

            report["comparison"] = {
                "label": "With Intelligence vs Technical Only",
                "primary_metrics": result.metrics,
                "comparison_metrics": comparison_result.metrics,
                "delta": self._calculate_delta(result.metrics, comparison_result.metrics),
            }

        return report

    def generate_summary_text(self, result: BacktestResult) -> str:
        """Genera riepilogo testuale leggibile.

        Args:
            result: Risultato del backtest.

        Returns:
            Testo riepilogativo.
        """
        if not result.metrics:
            self._calculator.calculate(result)

        m = result.metrics
        lines = [
            f"═══ Backtest Report: {result.config.symbol} ═══",
            f"Period: {result.config.start_date.date()} → {result.config.end_date.date()}",
            f"Initial Capital: ${float(result.config.initial_capital):.2f}",
            f"Intelligence: {'ON' if result.config.use_intelligence else 'OFF'}",
            "",
            f"📊 Performance:",
            f"  Total Trades: {m.get('total_trades', 0)}",
            f"  Win Rate: {m.get('win_rate', 0) * 100:.1f}%",
            f"  Total PnL: ${m.get('total_pnl', 0):.2f} ({m.get('total_pnl_pct', 0):.2f}%)",
            f"  Profit Factor: {m.get('profit_factor', 0):.2f}x",
            f"  Max Drawdown: {m.get('max_drawdown', 0) * 100:.1f}%",
            f"  Sharpe Ratio: {m.get('sharpe_ratio', 0):.2f}",
            f"  Avg Win: ${m.get('avg_win', 0):.2f}",
            f"  Avg Loss: ${m.get('avg_loss', 0):.2f}",
            f"  Consecutive Losses: {m.get('consecutive_losses', 0)}",
            f"  Signal Correlation: {m.get('signal_correlation', 0):.2f}",
            "",
            f"⏱ Duration: {result.duration_seconds:.1f}s" if result.duration_seconds else "",
            f"⚠ Errors: {len(result.errors)}" if result.errors else "",
        ]
        return "\n".join(filter(None, lines))

    # ─────────────────────────────
    # Metodi privati
    # ─────────────────────────────

    @staticmethod
    def _serialize_config(config: BacktestConfig) -> Dict[str, Any]:
        """Serializza config in dict."""
        return {
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "initial_capital": float(config.initial_capital),
            "use_intelligence": config.use_intelligence,
            "min_confidence": config.min_confidence,
            "commission_pct": float(config.commission_pct),
            "slippage_pct": float(config.slippage_pct),
        }

    @staticmethod
    def _generate_summary(result: BacktestResult) -> Dict[str, Any]:
        """Riepilogo esecutivo."""
        m = result.metrics
        total_pnl = m.get("total_pnl", 0)
        win_rate = m.get("win_rate", 0)
        sharpe = m.get("sharpe_ratio", 0)

        if total_pnl > 0 and win_rate > 0.5 and sharpe > 1:
            verdict = "positive"
            recommendation = "Strategy shows promising results. Consider paper trading."
        elif total_pnl < 0 or sharpe < 0:
            verdict = "negative"
            recommendation = "Strategy underperforms. Review signal logic and risk parameters."
        else:
            verdict = "neutral"
            recommendation = "Mixed results. More data or parameter tuning needed."

        return {
            "verdict": verdict,
            "recommendation": recommendation,
            "total_trades": m.get("total_trades", 0),
            "final_capital": float(result.config.initial_capital) + total_pnl,
            "total_pnl": total_pnl,
            "total_pnl_pct": m.get("total_pnl_pct", 0),
            "signal_correlation_quality": "positive" if m.get("signal_correlation", 0) > 0.3 else (
                "negative" if m.get("signal_correlation", 0) < -0.3 else "weak"
            ),
        }

    @staticmethod
    def _serialize_trades(trades: List) -> List[Dict[str, Any]]:
        """Serializza lista trade."""
        return [
            {
                "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": float(t.entry_price) if t.entry_price else None,
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "quantity": float(t.quantity) if t.quantity else None,
                "pnl": float(t.pnl) if t.pnl is not None else None,
                "pnl_pct": float(t.pnl_pct) if t.pnl_pct is not None else None,
                "signal_score": t.signal_score,
                "signal_type": t.signal_type,
                "status": t.status,
            }
            for t in trades
        ]

    @staticmethod
    def _equity_curve_preview(equity_curve: List[Dict]) -> List[Dict]:
        """Equity curve con campionamento per preview."""
        if len(equity_curve) <= 100:
            return equity_curve
        # Campiona 100 punti equidistanti
        step = len(equity_curve) // 100
        sampled = [equity_curve[i] for i in range(0, len(equity_curve), step)]
        if equity_curve[-1] not in sampled:
            sampled.append(equity_curve[-1])
        return sampled

    @staticmethod
    def _calculate_delta(
        primary: Dict[str, float],
        comparison: Dict[str, float],
    ) -> Dict[str, float]:
        """Delta tra due set di metriche."""
        delta = {}
        for key in primary:
            if key in comparison:
                delta[key] = round(primary[key] - comparison[key], 4)
        return delta