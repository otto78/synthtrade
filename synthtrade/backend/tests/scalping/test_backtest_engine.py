"""Tests per Backtest Engine (TASK-808).

Copre: BacktestConfig validazione, HistoricalLoader mock,
BacktestEngine run, PerformanceCalculator metriche, ReportGenerator,
e correlazione signal_score → outcome.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scalping.models.backtest import (
    BacktestConfig,
    SimulatedTrade,
    BacktestResult,
    BacktestMetric,
)
from app.scalping.backtest.backtest_engine import BacktestEngine
from app.scalping.backtest.historical_loader import HistoricalLoader
from app.scalping.backtest.performance_calculator import PerformanceCalculator
from app.scalping.backtest.report_generator import ReportGenerator
from app.scalping.models.market import Candle


# ─── Fixtures ───────────────────────────────────────────


@pytest.fixture
def sample_candles() -> list:
    """100 candele orarie simulate per BTCUSDT."""
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = Decimal("50000")
    for i in range(100):
        candles.append(Candle(
            symbol="BTCUSDT",
            open=price,
            high=price + Decimal("100"),
            low=price - Decimal("100"),
            close=price,
            volume=Decimal("100"),
            timestamp=dt,
            closed=True,
        ))
        price += Decimal("10")  # Lievemente rialzista
        dt = dt.replace(hour=(dt.hour + 1) % 24)
    return candles


@pytest.fixture
def basic_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="BTCUSDT",
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
        initial_capital=Decimal("1000"),
        use_intelligence=False,
    )


# ─── Test 1-3: BacktestConfig validazione ────────────────


class TestBacktestConfig:
    def test_valid_config(self):
        """Config con dati validi."""
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        assert config.symbol == "BTCUSDT"
        assert config.timeframe == "1h"
        assert config.initial_capital == Decimal("1000")

    def test_end_date_must_be_after_start(self):
        """end_date dopo start_date."""
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            BacktestConfig(
                symbol="BTCUSDT",
                start_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_invalid_timeframe(self):
        """timeframe non valido."""
        with pytest.raises(ValueError, match="timeframe must be one of"):
            BacktestConfig(
                symbol="BTCUSDT",
                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
                timeframe="3m",
            )

    def test_duration_hours_property(self):
        """Calcolo durata in ore."""
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
        assert config.duration_hours == 48.0


# ─── Test 4&5: SimulatedTrade ────────────────────────────


class TestSimulatedTrade:
    def test_close_buy_trade(self):
        """Chiusura trade BUY calcola P&L correttamente."""
        trade = SimulatedTrade(
            entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            symbol="BTCUSDT",
            side="BUY",
            entry_price=Decimal("50000"),
            quantity=Decimal("0.01"),
        )
        trade.close(
            exit_price=Decimal("51000"),
            exit_time=datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
            commission=Decimal("1"),
        )
        assert trade.is_closed
        # commission * 2 = 2 (entry + exit), raw_pnl = (51000-50000)*0.01 = 10, net = 10 - 2 = 8
        assert trade.pnl == Decimal("8.00")
        # pnl_pct = (8.00 / (50000*0.01)) * 100 = (8/500)*100 = 1.6%
        assert trade.pnl_pct == Decimal("1.600")

    def test_trade_properties(self):
        """Proprietà total_trades, winning_trades, losing_trades."""
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        result = BacktestResult(
            config=config,
            trades=[
                SimulatedTrade(
                    entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    symbol="BTCUSDT", side="BUY",
                    entry_price=Decimal("100"), quantity=Decimal("1"),
                    pnl=Decimal("10"), status="closed", exit_price=Decimal("110"),
                    exit_time=datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
                ),
                SimulatedTrade(
                    entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    symbol="BTCUSDT", side="BUY",
                    entry_price=Decimal("100"), quantity=Decimal("1"),
                    pnl=Decimal("-5"), status="closed", exit_price=Decimal("95"),
                    exit_time=datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
                ),
            ],
        )
        assert result.total_trades == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 1


# ─── Test 6: HistoricalLoader mock candles ────────────────


class TestHistoricalLoader:
    def test_generate_mock_candles_count(self):
        """generate_mock_candles produce il numero corretto di candele."""
        candles = HistoricalLoader.generate_mock_candles(
            symbol="BTCUSDT", count=50, start_price=Decimal("50000")
        )
        assert len(candles) == 50
        assert all(c.symbol == "BTCUSDT" for c in candles)
        assert candles[0].timestamp < candles[-1].timestamp


# ─── Test 7&8: BacktestEngine ────────────────────────────


class TestBacktestEngine:
    @pytest.mark.asyncio
    async def test_run_with_empty_candles(self, basic_config):
        """Backtest con candele vuote restituisce errore."""
        engine = BacktestEngine()
        result = await engine.run(basic_config, candles=[])
        assert len(result.errors) == 1
        assert "No candles" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_with_mock_candles(self, basic_config, sample_candles):
        """Backtest esegue trades su candele mock."""
        engine = BacktestEngine()
        result = await engine.run(basic_config, candles=sample_candles)

        assert result.id != ""
        assert len(result.trades) >= 0  # Può non fare trade ma non deve crashare
        assert len(result.equity_curve) == len(sample_candles) + 1
        assert result.completed_at is not None
        assert result.duration_seconds is not None

    @pytest.mark.asyncio
    async def test_run_with_progress_callback(self, basic_config, sample_candles):
        """Callback di progresso viene chiamato."""
        calls = []

        def progress(current, total):
            calls.append((current, total))

        engine = BacktestEngine()
        await engine.run(basic_config, candles=sample_candles, progress_callback=progress)

        assert len(calls) == len(sample_candles)
        assert calls[-1] == (len(sample_candles), len(sample_candles))


# ─── Test 9-11: PerformanceCalculator ────────────────────


class TestPerformanceCalculator:
    def test_empty_trades_metrics(self):
        """Metriche vuote quando non ci sono trade."""
        result = BacktestResult(
            config=BacktestConfig(
                symbol="BTCUSDT",
                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
            ),
        )
        calc = PerformanceCalculator()
        metrics = calc.calculate(result)
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0

    def test_win_rate_calculation(self):
        """Win rate calcolato correttamente."""
        trades = [
            SimulatedTrade(entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                           symbol="BTCUSDT", side="BUY", entry_price=Decimal("100"),
                           quantity=Decimal("1"), pnl=Decimal("10"), status="closed",
                           exit_price=Decimal("110"),
                           exit_time=datetime(2026, 1, 1, 2, tzinfo=timezone.utc)),
            SimulatedTrade(entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                           symbol="BTCUSDT", side="BUY", entry_price=Decimal("100"),
                           quantity=Decimal("1"), pnl=Decimal("-5"), status="closed",
                           exit_price=Decimal("95"),
                           exit_time=datetime(2026, 1, 1, 2, tzinfo=timezone.utc)),
            SimulatedTrade(entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                           symbol="BTCUSDT", side="BUY", entry_price=Decimal("100"),
                           quantity=Decimal("1"), pnl=Decimal("3"), status="closed",
                           exit_price=Decimal("103"),
                           exit_time=datetime(2026, 1, 1, 2, tzinfo=timezone.utc)),
        ]
        result = BacktestResult(
            config=BacktestConfig(
                symbol="BTCUSDT",
                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
                initial_capital=Decimal("1000"),
            ),
            trades=trades,
        )
        calc = PerformanceCalculator()
        metrics = calc.calculate(result)
        assert metrics["win_rate"] == pytest.approx(2 / 3, rel=0.01)
        assert metrics["total_trades"] == 3
        assert metrics["profit_factor"] == pytest.approx(13 / 5, rel=0.01)

    def test_max_drawdown_calculation(self):
        """Max drawdown calcolato da equity curve."""
        equity_curve = [
            {"timestamp": "2026-01-01T00:00:00Z", "equity": 1000},
            {"timestamp": "2026-01-01T01:00:00Z", "equity": 1100},
            {"timestamp": "2026-01-01T02:00:00Z", "equity": 900},
            {"timestamp": "2026-01-01T03:00:00Z", "equity": 950},
            {"timestamp": "2026-01-01T04:00:00Z", "equity": 1050},
        ]
        calc = PerformanceCalculator()
        dd = calc._max_drawdown(equity_curve)
        assert dd == pytest.approx((1100 - 900) / 1100, rel=0.01)

    def test_pearson_correlation(self):
        """Correlazione Pearson."""
        calc = PerformanceCalculator()
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = calc._pearson_correlation(x, y)
        assert corr == pytest.approx(1.0, rel=0.01)


# ─── Test 12-14: ReportGenerator ─────────────────────────


class TestReportGenerator:
    def test_generate_report_structure(self):
        """Report ha struttura corretta."""
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        result = BacktestResult(config=config)
        result.metrics = {"total_trades": 5, "win_rate": 0.6, "total_pnl": 100.0}
        result.correlation_data = {"pearson": 0.5, "spearman": 0.4}

        gen = ReportGenerator()
        report = gen.generate_report(result)

        assert "report_id" in report
        assert "config" in report
        assert "summary" in report
        assert "metrics" in report
        assert "correlation" in report
        assert "trades" in report

    def test_generate_report_with_comparison(self):
        """Report con confronto with/without intelligence."""
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        result1 = BacktestResult(config=config)
        result1.metrics = {"total_trades": 5, "win_rate": 0.6, "total_pnl": 100.0}
        result1.correlation_data = {"pearson": 0.5, "spearman": 0.4}

        result2 = BacktestResult(config=config)
        result2.metrics = {"total_trades": 8, "win_rate": 0.5, "total_pnl": 50.0}
        result2.correlation_data = {"pearson": 0.3, "spearman": 0.2}

        gen = ReportGenerator()
        report = gen.generate_report(result1, comparison_result=result2)

        assert "comparison" in report
        assert "delta" in report["comparison"]
        assert report["comparison"]["delta"]["total_pnl"] == 50.0

    def test_summary_text_format(self):
        """Testo riepilogo ha formato leggibile."""
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        result = BacktestResult(config=config)
        result.metrics = {"total_trades": 3, "win_rate": 0.667, "total_pnl": 50.0}

        gen = ReportGenerator()
        text = gen.generate_summary_text(result)

        assert "BTCUSDT" in text
        assert "Win Rate" in text
        assert "50.0" in text


# ─── Test 15: BacktestEngine calcolo quantity ─────────────


class TestBacktestEngineUtils:
    def test_calculate_quantity(self):
        """Calcolo quantità basato su capitale."""
        engine = BacktestEngine()
        config = BacktestConfig(
            symbol="BTCUSDT",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
            initial_capital=Decimal("1000"),
        )
        qty = engine._calculate_quantity(Decimal("1000"), Decimal("50000"), config)
        assert qty == Decimal("0.019")  # 950 / 50000 = 0.019


# ─── Test 16: HistoricalLoader CSV fallisce se file non esiste ──


class TestHistoricalLoaderErrors:
    def test_csv_file_not_found(self):
        """File CSV inesistente solleva FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="test_inesistente.csv"):
            HistoricalLoader.load_from_csv("test_inesistente.csv", "BTCUSDT")


# ─── Test 17: SimulatedTrade edge cases ──────────────────


class TestSimulatedTradeEdgeCases:
    def test_trade_is_closed_only_when_closed(self):
        """is_closed proprieta' corretta."""
        trade = SimulatedTrade(
            entry_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            symbol="BTCUSDT", side="BUY",
            entry_price=Decimal("100"), quantity=Decimal("1"),
        )
        assert not trade.is_closed
        trade.close(Decimal("110"), datetime(2026, 1, 1, 2, tzinfo=timezone.utc))
        assert trade.is_closed