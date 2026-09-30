"""Tests for scalping scheduler jobs (TASK-807)."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
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
        ), patch(
            "app.scalping.router._execution_state",
            self._RUNNING_SESSION_STATE,
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
        ), patch(
            "app.scalping.router._execution_state",
            self._RUNNING_SESSION_STATE,
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
        """Health job verifica che engine e stato siano configurati."""
        from app.scalping import router as scalping_router
        ws_client = MagicMock()
        ws_client._stop_event = asyncio.Event()
        state = {
            "session": {
                "status": "running",
                "symbol": "BNBUSDC",
                "mode": "live",
            },
            "ws_client": ws_client,
            "loop": MagicMock(_candle_buffer=MagicMock(__len__=lambda self: 100)),
            "ws_tasks": [],
        }
        with patch("app.scheduler.scalping_jobs._engine", MagicMock()), patch.dict(
            scalping_router._execution_state,
            state,
            clear=True,
        ), patch("app.scheduler.scalping_jobs.logger") as mock_logger:
            await session_health_job()
            assert mock_logger.debug.call_args_list[-1] == call(
                "Session health check OK: status=running, symbol=BNBUSDC, "
                "mode=live, tasks=0, buffer_ready=True"
            )


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
        """Verifica che i job non vengano registrati se scalping è disabilitato."""
        import app.scheduler.jobs as jobs_mod

        fresh_scheduler = AsyncIOScheduler()
        mock_settings = MagicMock()
        mock_settings.SWING_JOBS_ENABLED = False
        mock_settings.scalping.SCALPING_DEFAULT_MODE = ""

        with patch.object(jobs_mod, "scheduler", fresh_scheduler), patch.object(
            jobs_mod,
            "settings",
            mock_settings,
        ):
            result = jobs_mod.setup_scheduler(engine=None)

        job_ids = [job.id for job in result.get_jobs()]
        assert not [job_id for job_id in job_ids if job_id.startswith("scalping_")]


# ── TASK-1272: spot_reconciliation non deve pausare per capitale in posizione ──

class TestSpotReconciliation:
    """La pausa SPOT_BALANCEZero era un falso positivo.

    `live_balance` e' `cashBal` di OKX (available + frozen), che include il
    capitale impegnato nella posizione aperta. Con capitale 21.9 EUR e trade da
    20 EUR, ogni posizione aperta portava il saldo a 1.87 EUR e la sessione
    veniva pausata con `pause_reason=SPOT_BALANCE_ZERO` e il messaggio "fondi in
    Simple Earn": entrambi falsi, perche' quei fondi erano nella nostra posizione.
    """

    @staticmethod
    def _state(balance, trade_value=20.0, status="running", has_open=False, notional=0.0):
        session = {"status": status, "mode": "live", "live_balance": balance,
                   "trade_value": trade_value}
        pm = MagicMock()
        pm.has_open.return_value = has_open
        pos = MagicMock()
        pos.quantity = notional / 73132.8 if notional else 0
        pos.entry_price = 73132.8
        pm.get_open.return_value = pos if has_open else None
        return {"session": session, "position_manager": pm}, session

    async def _run(self, state):
        from app.scheduler.scalping_jobs import spot_reconciliation_job
        broadcast = AsyncMock()
        with patch("app.scheduler.scalping_jobs.settings") as ms, \
             patch("app.scalping.router._execution_state", state), \
             patch("app.scalping.router._refresh_session_balance", AsyncMock()), \
             patch("app.scalping.router.broadcast_scalping_event", broadcast):
            ms.scalping.SCALPING_SCHEDULER_HEALTH_ENABLED = True
            await spot_reconciliation_job()
        return state["session"], broadcast

    @pytest.mark.asyncio
    async def test_does_not_pause_when_funds_are_in_open_position(self):
        """Saldo basso MA posizione aperta = capitale impegnato, NON una pausa."""
        state, session = self._state(1.87, has_open=True, notional=20.0)
        session, broadcast = await self._run(state)
        assert session["status"] == "running", "non deve pausare con posizione aperta"
        assert broadcast.await_count == 0, "non deve broadcastare nulla"

    @pytest.mark.asyncio
    async def test_pauses_when_no_position_and_balance_insufficient(self):
        """Saldo basso e NESSUNA posizione = fondi non disponibili = pausa legittima."""
        state, session = self._state(1.87, has_open=False)
        session, broadcast = await self._run(state)
        assert session["status"] == "paused"
        payload = broadcast.await_args_list[0].args[1]
        assert payload["pause_reason"] == "SPOT_BALANCE_INSUFFICIENT"
        assert "Simple Earn" in payload["pause_message"], "deve ancora suggerire di verificare Earn"
        assert "posizione aperta" in payload["pause_message"], "deve dire che non c'e' una posizione"

    @pytest.mark.asyncio
    async def test_reason_is_not_the_false_zero(self):
        """'SPOT_BALANCE_ZERO' era un bug: il saldo non e' zero, e' impegnato."""
        state, session = self._state(0.5, has_open=False)
        session, broadcast = await self._run(state)
        payload = broadcast.await_args_list[0].args[1]
        assert payload["pause_reason"] != "SPOT_BALANCE_ZERO"

    @pytest.mark.asyncio
    async def test_resumes_when_balance_sufficient(self):
        """Con saldo sufficiente e sessione in pausa, deve riprendere."""
        state, session = self._state(21.9, status="paused", has_open=False)
        session, broadcast = await self._run(state)
        assert session["status"] == "running"
        assert broadcast.await_count == 1

    @pytest.mark.asyncio
    async def test_position_open_with_ample_balance_stays_running(self):
        """Caso normale: saldo abbondante e posizione aperta, resta running."""
        state, session = self._state(21.9, has_open=True, notional=20.0)
        session, broadcast = await self._run(state)
        assert session["status"] == "running"
        assert broadcast.await_count == 0
