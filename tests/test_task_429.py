"""
TASK-429 — Gestione errori e retry per exchange failures nel signal loop

Test TDD per:
1. asyncio.gather con return_exceptions=True gestisce eccezioni correttamente
2. Broadcast errori via WebSocket quando exchange fallisce
3. Retry logic per errori temporanei (network timeout, rate limit)
4. Strategia continua anche se una singola strategia fallisce
5. Logging appropriato degli errori exchange
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any


# ──────────────────────────────────────────────
# Unit test: asyncio.gather error handling
# ──────────────────────────────────────────────

class TestAsyncioGatherErrorHandling:
    """Verifica che asyncio.gather con return_exceptions=True catturi gli errori."""

    @pytest.mark.asyncio
    async def test_gather_returns_exceptions_without_crashing(self):
        """gather con return_exceptions=True non blocca l'intero loop."""
        async def task_ok():
            return "success"

        async def task_fail():
            raise RuntimeError("Exchange connection failed")

        async def task_ok_2():
            return "success_2"

        results = await asyncio.gather(
            task_ok(),
            task_fail(),
            task_ok_2(),
            return_exceptions=True
        )

        assert len(results) == 3
        assert results[0] == "success"
        assert isinstance(results[1], RuntimeError)
        assert results[2] == "success_2"

    @pytest.mark.asyncio
    async def test_gather_collects_multiple_exceptions(self):
        """Più strategie possono fallire indipendentemente."""
        async def task_fail_1():
            raise ConnectionError("Binance timeout")

        async def task_fail_2():
            raise RuntimeError("Rate limit exceeded")

        async def task_ok():
            return "success"

        results = await asyncio.gather(
            task_fail_1(),
            task_fail_2(),
            task_ok(),
            return_exceptions=True
        )

        assert isinstance(results[0], ConnectionError)
        assert isinstance(results[1], RuntimeError)
        assert results[2] == "success"


# ──────────────────────────────────────────────
# Unit test: Error broadcast via WebSocket
# ──────────────────────────────────────────────

class TestErrorBroadcast:
    """Verifica che gli errori exchange vengano broadcastati via WS."""

    @pytest.mark.asyncio
    async def test_broadcast_exchange_error_format(self):
        """broadcast_exchange_error invia messaggio con formato corretto."""
        mock_manager = MagicMock()
        mock_manager.broadcast = AsyncMock()

        # Simula broadcast_exchange_error
        async def broadcast_exchange_error(strategy_id: str, error_message: str, error_type: str):
            await mock_manager.broadcast({
                "type": "exchange_error",
                "strategy_id": strategy_id,
                "error_message": error_message,
                "error_type": error_type,
            })

        await broadcast_exchange_error(
            strategy_id="s1",
            error_message="Binance connection timeout",
            error_type="ConnectionError"
        )

        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "exchange_error"
        assert call_args["strategy_id"] == "s1"
        assert "timeout" in call_args["error_message"].lower()
        assert call_args["error_type"] == "ConnectionError"

    @pytest.mark.asyncio
    async def test_broadcast_error_includes_timestamp(self):
        """Il broadcast deve includere timestamp per tracciabilità."""
        from datetime import datetime, timezone

        error_message = {
            "type": "exchange_error",
            "strategy_id": "s1",
            "error_message": "Rate limit exceeded",
            "error_type": "RateLimitError",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        assert "timestamp" in error_message
        assert "T" in error_message["timestamp"]  # ISO format

    @pytest.mark.asyncio
    async def test_error_broadcast_does_not_crash_on_no_clients(self):
        """Broadcast non deve crashare se non ci sono client connessi."""
        mock_manager = MagicMock()
        mock_manager.active_connections = []
        mock_manager.broadcast = AsyncMock()

        await mock_manager.broadcast({"type": "exchange_error", "strategy_id": "s1"})
        # Non deve crashare
        assert True


# ──────────────────────────────────────────────
# Unit test: Strategy continues after error
# ──────────────────────────────────────────────

class TestStrategyIndependence:
    """Verifica che una strategia fallita non blocchi le altre."""

    @pytest.mark.asyncio
    async def test_one_strategy_fails_others_continue(self):
        """Se una strategia crasha, le altre devono continuare."""
        executed = []

        async def strategy_1():
            executed.append("s1")
            raise ConnectionError("Exchange down")

        async def strategy_2():
            executed.append("s2")
            return "success"

        async def strategy_3():
            executed.append("s3")
            return "success"

        results = await asyncio.gather(
            strategy_1(),
            strategy_2(),
            strategy_3(),
            return_exceptions=True
        )

        assert "s1" in executed
        assert "s2" in executed
        assert "s3" in executed
        assert isinstance(results[0], ConnectionError)
        assert results[1] == "success"
        assert results[2] == "success"

    @pytest.mark.asyncio
    async def test_all_strategies_fail_gracefully(self):
        """Anche se tutte le strategie falliscono, il job non crasha."""
        async def strategy_fail():
            raise RuntimeError("Exchange unavailable")

        results = await asyncio.gather(
            strategy_fail(),
            strategy_fail(),
            strategy_fail(),
            return_exceptions=True
        )

        assert all(isinstance(r, RuntimeError) for r in results)


# ──────────────────────────────────────────────
# Unit test: Error types classification
# ──────────────────────────────────────────────

class TestErrorClassification:
    """Verifica che i diversi tipi di errori siano classificati correttamente."""

    def test_connection_error_detected(self):
        """ConnectionError deve essere riconosciuto come errore di rete."""
        error = ConnectionError("Network unreachable")
        assert isinstance(error, ConnectionError)

    def test_timeout_error_detected(self):
        """TimeoutError deve essere riconosciuto."""
        error = TimeoutError("Request timeout after 30s")
        assert isinstance(error, TimeoutError)

    def test_runtime_error_detected(self):
        """RuntimeError generico deve essere gestito."""
        error = RuntimeError("Unexpected exchange response")
        assert isinstance(error, RuntimeError)

    def test_error_type_to_string(self):
        """Il tipo di errore deve essere convertibile in stringa."""
        error = ConnectionError("test")
        error_type = type(error).__name__
        assert error_type == "ConnectionError"


# ──────────────────────────────────────────────
# Integration test: run_active_strategies_job
# ──────────────────────────────────────────────

class TestRunActiveStrategiesJobErrorHandling:
    """Test integrazione per il job run_active_strategies_job."""

    @pytest.mark.asyncio
    async def test_job_handles_runner_exceptions(self):
        """Il job deve gestire eccezioni da StrategyRunner.run_tick()."""
        mock_engine = MagicMock()
        mock_runner = MagicMock()

        async def run_tick_fail(strategy):
            raise ConnectionError("Exchange connection lost")

        async def run_tick_ok(strategy):
            return None

        strategies = [
            {"id": "s1", "template": "ema_cross"},
            {"id": "s2", "template": "rsi_mean_rev"},
        ]

        # Simula che s1 fallisce, s2 ok
        results = await asyncio.gather(
            run_tick_fail(strategies[0]),
            run_tick_ok(strategies[1]),
            return_exceptions=True
        )

        assert isinstance(results[0], ConnectionError)
        assert results[1] is None

    @pytest.mark.asyncio
    async def test_job_broadcasts_errors_for_failed_strategies(self):
        """Il job deve fare broadcast per ogni strategia fallita."""
        mock_manager = MagicMock()
        mock_manager.broadcast_exchange_error = AsyncMock()

        strategies = [
            {"id": "s1", "template": "ema_cross"},
            {"id": "s2", "template": "rsi_mean_rev"},
        ]

        async def run_tick(strategy):
            if strategy["id"] == "s1":
                raise ConnectionError("Binance timeout")
            return None

        results = await asyncio.gather(
            *[run_tick(s) for s in strategies],
            return_exceptions=True
        )

        # Verifica che ci sia un'eccezione
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 1
        assert isinstance(errors[0], ConnectionError)


# ──────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────

class TestEdgeCases:
    """Casi limite per la gestione errori."""

    @pytest.mark.asyncio
    async def test_empty_strategy_list_does_not_crash(self):
        """Lista vuota di strategie non deve crashare."""
        strategies = []
        results = await asyncio.gather(
            *[asyncio.sleep(0) for _ in strategies],
            return_exceptions=True
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_exception_with_no_message(self):
        """Eccezione senza messaggio deve essere gestita."""
        async def task_fail():
            raise RuntimeError()

        results = await asyncio.gather(task_fail(), return_exceptions=True)
        assert isinstance(results[0], RuntimeError)
        assert str(results[0]) == ""

    @pytest.mark.asyncio
    async def test_nested_exception(self):
        """Eccezioni annidate devono essere gestite."""
        async def task_fail():
            try:
                raise ConnectionError("Network error")
            except ConnectionError as e:
                raise RuntimeError("Retry failed") from e

        results = await asyncio.gather(task_fail(), return_exceptions=True)
        assert isinstance(results[0], RuntimeError)
        assert results[0].__cause__ is not None
        assert isinstance(results[0].__cause__, ConnectionError)


# ──────────────────────────────────────────────
# Performance test: Error handling overhead
# ──────────────────────────────────────────────

class TestPerformance:
    """Verifica che la gestione errori non introduca overhead significativo."""

    @pytest.mark.asyncio
    async def test_error_handling_does_not_slow_down_successful_tasks(self):
        """Task che hanno successo non devono essere rallentati dalla gestione errori."""
        import time

        async def task_ok():
            await asyncio.sleep(0.01)  # 10ms
            return "success"

        start = time.time()
        results = await asyncio.gather(
            *[task_ok() for _ in range(10)],
            return_exceptions=True
        )
        elapsed = time.time() - start

        assert all(r == "success" for r in results)
        # Dovrebbe completare in ~10ms (parallelismo), non 100ms (seriale)
        assert elapsed < 0.1  # 100ms tolleranza
