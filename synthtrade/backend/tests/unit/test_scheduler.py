import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.scheduler.jobs import run_pipeline_job, monitor_positions_job, heartbeat_job


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.close_position_if_needed = AsyncMock()
    engine.order_tracker = MagicMock()
    return engine


@pytest.mark.asyncio
async def test_run_pipeline_job_calls_run_pipeline():
    with patch("app.scheduler.jobs.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = AsyncMock()
        await run_pipeline_job()
        mock_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_positions_job_calls_close_for_each(mock_engine):
    from app.execution.schemas import PositionSnapshot
    from datetime import datetime, UTC
    pos = PositionSnapshot(
        trade_id="t1", strategy_id="s1", symbol="BTC/USDT",
        direction="BUY", entry_price=60000.0, quantity=0.01,
        stop_loss=58800.0, take_profit=62400.0, opened_at=datetime.now(UTC)
    )
    mock_engine.order_tracker.get_open_positions.return_value = [pos]

    with patch("app.scheduler.jobs.get_current_price", return_value=61000.0):
        await monitor_positions_job(mock_engine)

    mock_engine.close_position_if_needed.assert_called_once_with(pos, 61000.0)


@pytest.mark.asyncio
async def test_heartbeat_job_broadcasts_ws():
    mock_broadcast = AsyncMock()
    with patch("app.scheduler.jobs.manager") as mock_manager:
        mock_manager.broadcast = mock_broadcast
        await heartbeat_job()
        mock_broadcast.assert_called_once()
        call_data = mock_broadcast.call_args[0][0]
        assert call_data["type"] == "heartbeat"
        assert "timestamp" in call_data


@pytest.mark.asyncio
async def test_exception_in_job_does_not_propagate():
    with patch("app.scheduler.jobs.run_pipeline", side_effect=Exception("boom")):
        # Non deve sollevare
        await run_pipeline_job()
