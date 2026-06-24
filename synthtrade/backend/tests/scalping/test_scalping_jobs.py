"""Tests for scalping scheduler jobs (TASK-807)."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.scalping_jobs import (
    intelligence_snapshot_job,
    funding_rate_update_job,
    supervisor_check_job,
    session_health_job,
    set_engine,
)


class TestScalpingJobs:
    """Test suite per i job periodici scalping."""

    _RUNNING_SESSION_STATE = {
        "session": {"symbol": "BTCUSDT", "status": "running"},
    }

    @pytest.mark.asyncio
    async def test_intel_snapshot_job_disabled(self):
        """Job non esegue nulla se disabilitato."""
        with patch("app.scheduler.scalping_jobs.settings") as mock_settings:
            mock_settings.scalping.SCALPING_SCHEDULER_INTEL_SNAPSHOT_ENABLED = False
            result = await intelligence_snapshot_job()
            assert result is None

    @pytest.mark.asyncio
    async def test_intel_snapshot_job_success(self):
        """Job esegue snapshot e logga risultato (patch sul modulo source)."""
        mock_snapshot = MagicMock()
        mock_snapshot.symbol = "BTCUSDT"
        mock_snapshot.funding_rate = None
        mock_snapshot.open_interest = None
        mock_snapshot.long_short_ratio = None
        mock_snapshot.cvd = None
        mock_snapshot.fear_greed = None
        mock_snapshot.signal_score = MagicMock()
        mock_snapshot.signal_score.total = 45.5
        mock_snapshot.signal_score.bias = "bullish"

        with patch(
            "app.scalping.intelligence.signal_score_engine.SignalScoreEngine.get_snapshot",
            new_callable=AsyncMock,
            return_value=mock_snapshot,
        ) as mock_get_snapshot, patch(
            "app.scalping.router._execution_state",
            self._RUNNING_SESSION_STATE,
        ):
            result = await intelligence_snapshot_job()
            assert result is None
            mock_get_snapshot.assert_called_once_with(force_refresh=True)

    @pytest.mark.asyncio
    async def test_intel_snapshot_job_handles_none_snapshot(self):
        """Job gestisce snapshot None."""
        with patch(
            "app.scalping.intelligence.signal_score_engine.SignalScoreEngine.get_snapshot",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.scalping.router._execution_state",
            self._RUNNING_SESSION_STATE,
        ):
            with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
                await intelligence_snapshot_job()
                mock_logger.warning.assert_called_once_with(
                    "Intel snapshot job: snapshot is None"
                )

    @pytest.mark.asyncio
    async def test_intel_snapshot_job_handles_exception(self):
        """Job gestisce eccezioni interne."""
        with patch(
            "app.scalping.intelligence.signal_score_engine.SignalScoreEngine.get_snapshot",
            new_callable=AsyncMock,
            side_effect=Exception("API error"),
        ), patch(
            "app.scalping.router._execution_state",
            self._RUNNING_SESSION_STATE,
        ):
            with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
                await intelligence_snapshot_job()
                mock_logger.error.assert_called_once()
                assert "API error" in str(mock_logger.error.call_args[0][0])

    @pytest.mark.asyncio
    async def test_funding_rate_job_disabled(self):
        """Funding rate job non esegue nulla se disabilitato."""
        with patch("app.scheduler.scalping_jobs.settings") as mock_settings:
            mock_settings.scalping.SCALPING_SCHEDULER_FUNDING_RATE_ENABLED = False
            result = await funding_rate_update_job()
            assert result is None

    @pytest.mark.asyncio
    async def test_funding_rate_job_success(self):
        """Funding rate job esegue collect per simboli configurati."""
        mock_fr = MagicMock()
        mock_fr.rate = 0.0001
        mock_fr.next_funding_time = "2026-05-25T12:00:00Z"

        with patch(
            "app.scalping.intelligence.collectors.funding_rate.FundingRateCollector.collect",
            new_callable=AsyncMock,
            return_value=mock_fr,
        ):
            with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
                await funding_rate_update_job()
                mock_logger.info.assert_any_call(
                    "Funding rate BTCUSDT: 0.0100% (next: 2026-05-25T12:00:00Z)"
                )
                mock_logger.info.assert_any_call(
                    "Funding rate ETHUSDT: 0.0100% (next: 2026-05-25T12:00:00Z)"
                )

    @pytest.mark.asyncio
    async def test_funding_rate_job_handles_symbol_error(self):
        """Funding rate job gestisce errore su un simbolo senza bloccare gli altri."""
        async def mock_collect(symbol):
            if symbol == "BTCUSDT":
                raise Exception("BTC API error")
            fr = MagicMock()
            fr.rate = 0.0002
            fr.next_funding_time = "2026-05-25T12:00:00Z"
            return fr

        with patch(
            "app.scalping.intelligence.collectors.funding_rate.FundingRateCollector.collect",
            new_callable=AsyncMock,
            side_effect=mock_collect,
        ):
            with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
                await funding_rate_update_job()
                mock_logger.warning.assert_called_once_with(
                    "Funding rate update for BTCUSDT failed: BTC API error"
                )
                mock_logger.info.assert_any_call(
                    "Funding rate ETHUSDT: 0.0200% (next: 2026-05-25T12:00:00Z)"
                )

    @pytest.mark.asyncio
    async def test_supervisor_job_disabled(self):
        """Supervisor job non esegue nulla se disabilitato."""
        with patch("app.scheduler.scalping_jobs.settings") as mock_settings:
            mock_settings.scalping.SCALPING_SCHEDULER_SUPERVISOR_ENABLED = False
            result = await supervisor_check_job()
            assert result is None

    @pytest.mark.asyncio
    async def test_supervisor_job_with_decision(self):
        """Supervisor job esegue e logga decisione."""
        mock_decision = MagicMock()
        mock_decision.action = "no_action"
        mock_decision.confidence = 0.85
        mock_decision.reason = "Market conditions normal"

        mock_scheduler = MagicMock()
        mock_scheduler.run_once = AsyncMock(return_value=mock_decision)

        # Patch sul modulo sorgente (lazy import inside the job function)
        with patch(
            "app.scalping.supervisor.supervisor_scheduler.SupervisorScheduler",
            return_value=mock_scheduler,
            create=True,
        ):
            with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
                await supervisor_check_job()
                mock_logger.info.assert_called_once()
                assert "no_action" in str(mock_logger.info.call_args[0][0])

    @pytest.mark.asyncio
    async def test_supervisor_job_no_decision(self):
        """Supervisor job gestisce assenza di decisione."""
        mock_scheduler = MagicMock()
        mock_scheduler.run_once = AsyncMock(return_value=None)

        with patch(
            "app.scalping.supervisor.supervisor_scheduler.SupervisorScheduler",
            return_value=mock_scheduler,
            create=True,
        ):
            with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
                await supervisor_check_job()
                mock_logger.debug.assert_called_once_with(
                    "Supervisor check: no decision returned (scheduler not running)"
                )

    @pytest.mark.asyncio
    async def test_health_job_disabled(self):
        """Health job non esegue nulla se disabilitato."""
        with patch("app.scheduler.scalping_jobs.settings") as mock_settings:
            mock_settings.scalping.SCALPING_SCHEDULER_HEALTH_ENABLED = False
            result = await session_health_job()
            assert result is None

    @pytest.mark.asyncio
    async def test_health_job_no_engine(self):
        """Health job logga debug se engine non impostato."""
        set_engine(None)
        with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
            await session_health_job()
            mock_logger.debug.assert_called_once_with(
                "Session health: engine not set (skipping)"
            )

    @pytest.mark.asyncio
    async def test_health_job_with_engine(self):
        """Health job esegue check con engine impostato."""
        set_engine(MagicMock())
        with patch("app.scheduler.scalping_jobs.logger") as mock_logger:
            await session_health_job()
            mock_logger.debug.assert_called_once_with("Session health check: OK")


class TestScalpingJobsRegistration:
    """Test per registrazione job in setup_scheduler."""

    def test_jobs_registered_in_setup_scheduler(self):
        """Verifica che setup_scheduler registri i job scalping."""
        from app.scheduler.jobs import setup_scheduler

        result = setup_scheduler(engine=None)

        try:
            job_ids = [job.id for job in result.get_jobs()]
            assert "scalping_intel_snapshot" in job_ids
            assert "scalping_funding_rate" in job_ids
            assert "scalping_supervisor_check" in job_ids
            assert "scalping_session_health" in job_ids
        finally:
            # Il scheduler non è stato startato, quindi non serve shutdown
            pass

    def test_jobs_not_registered_when_scalping_disabled(self):
        """Verifica che i job NON vengano registrati se scalping è disabilitato."""
        import importlib
        import app.scheduler.jobs as jobs_mod

        # Ricarica il modulo per avere un scheduler pulito
        importlib.reload(jobs_mod)

        scalping_obj = jobs_mod.settings.scalping
        orig_mode = scalping_obj.SCALPING_DEFAULT_MODE

        try:
            scalping_obj.SCALPING_DEFAULT_MODE = ""
            result = jobs_mod.setup_scheduler(engine=None)
            job_ids = [job.id for job in result.get_jobs()]
            assert "scalping_intel_snapshot" not in job_ids
            assert "scalping_funding_rate" not in job_ids
            assert "scalping_supervisor_check" not in job_ids
            assert "scalping_session_health" not in job_ids
        finally:
            scalping_obj.SCALPING_DEFAULT_MODE = orig_mode
