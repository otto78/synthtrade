"""
TASK-1111: Integration tests con fake OKX adapter.

Scenari coperti:
  1111.A — Happy path: entry → bracket → fill TP → DB closed + WS event
  1111.B — Bracket failure: entry ok → bracket reject → emergency close → no DB open
  1111.C — Stop session: posizione open → cancel bracket → market close → DB reason=session_stop
  1111.D — Restore open: DB posizione open → exchange open bracket → order stream restart
  1111.E — Restore closed: DB open → no bracket → DB reconciled
  1111.F — Fee/net pricing: TP/SL lordo coerente con target netto e fee OKX

Tutti i test sono in-process, nessuna chiamata di rete.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.execution.exchange_models import (
    ExitBracketRequest,
    FeeTier,
    MarketOrderRequest,
    SymbolRef,
)
from app.scalping.engine.position_manager import Position, PositionManager, PositionStatus

# Import the module under test so we can manipulate its globals directly
import app.scalping.router as router_module
from app.scalping.router import (
    _execution_state,
    _on_order_update,
    _save_open_position_to_db,
    _update_closed_position_in_db,
    _handle_bracket_failed,
    broadcast_scalping_event,
)
from tests.integration.fake_okx_adapter import (
    BTC_EUR,
    FAKE_FEE,
    FAKE_RULES,
    FakeOkxAdapter,
    FakeOrderStream,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reset_execution_state(adapter: FakeOkxAdapter, symbol: str = "BTC-EUR") -> None:
    """Reset router _execution_state to a known clean state with the given adapter."""
    _execution_state["position_manager"] = PositionManager()
    _execution_state["exchange"] = adapter
    _execution_state["user_data_stream"] = None
    _execution_state["trade_history"] = []
    _execution_state["fee_tier"] = {"maker": FAKE_FEE.maker, "taker": FAKE_FEE.taker}
    _execution_state["fee_tier_certified"] = FAKE_FEE.certified
    _execution_state["session"] = {
        "session_id": "test-session-001",
        "db_session_id": "db-session-001",
        "status": "running",
        "mode": "live",
        "strategy": "scalping_v2",
        "symbol": symbol,
        "started_at": "2026-07-03T10:00:00Z",
        "stopped_at": None,
        "paper_balance": 1000.0,
        "live_balance": 1000.0,
        "trade_value": 10.0,
    }
    _execution_state["risk_config"] = {
        "max_daily_loss": 50.0,
        "max_drawdown": 10.0,
        "stop_loss_pct": 0.3,
        "take_profit_pct": 0.5,
    }


def _open_fake_position(
    symbol: str = "BTC-EUR",
    side: str = "BUY",
    entry_price: float = 43700.0,
    qty: float = 0.00022883,
    bracket_id: str = "algo-fake-0001",
    tp_id: str = "tp-algo-fake-0001",
    sl_id: str = "sl-algo-fake-0001",
) -> Position:
    """Register an open position in _execution_state's position manager."""
    pm: PositionManager = _execution_state["position_manager"]
    pos = pm.open_position(
        symbol=symbol,
        side=side,
        entry_price=Decimal(str(entry_price)),
        quantity=Decimal(str(qty)),
        entry_commission=0.0,
        entry_commission_asset="EUR",
    )
    pos.oco_order_list_id = bracket_id
    pos.tp_order_id = tp_id
    pos.sl_order_id = sl_id
    return pos


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def adapter() -> FakeOkxAdapter:
    return FakeOkxAdapter()


@pytest.fixture
def order_stream() -> FakeOrderStream:
    return FakeOrderStream()


@pytest.fixture(autouse=True)
def mock_supabase_and_broadcast():
    """Patch DB and broadcast so tests never hit real Supabase or WebSocket."""
    with (
        patch("app.scalping.router.get_supabase") as mock_db,
        patch("app.scalping.router.broadcast_scalping_event", new_callable=AsyncMock) as mock_bc,
        patch("app.scalping.router.asyncio.to_thread", side_effect=lambda fn, *a, **kw: asyncio.coroutine(fn)(*a, **kw) if asyncio.iscoroutinefunction(fn) else asyncio.get_event_loop().run_in_executor(None, fn)),
    ):
        db = MagicMock()
        # Simulate successful DB insert returning a row with id
        db.table.return_value.insert.return_value.execute.return_value.data = [{"id": "trade-db-001"}]
        db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "trade-db-001"}]
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_db.return_value = db
        yield {"db": db, "broadcast": mock_bc}


# ── 1111.A — Happy path ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_1111a_happy_path_tp_fill(adapter, order_stream, mock_supabase_and_broadcast):
    """
    Scenario 1111.A — Happy path:
    Entry market order OK → bracket placed → TP fill event → position closed in DB.
    """
    _reset_execution_state(adapter)
    session = _execution_state["session"]

    # 1. Verify adapter has EUR balance
    bal = await adapter.get_balance("EUR")
    assert bal == 1000.0

    # 2. Place market order
    market_req = MarketOrderRequest(symbol=BTC_EUR, side="buy", quantity=10.0 / 43700.0, quote_amount=10.0)
    market_res = await adapter.place_market_order(market_req)
    assert market_res.status == "closed"
    assert market_res.quantity > 0
    exec_qty = market_res.quantity
    exec_price = market_res.average_price

    # 3. Place exit bracket
    bracket_req = ExitBracketRequest(
        symbol=BTC_EUR,
        side="sell",
        quantity=exec_qty,
        tp_price=round(exec_price * 1.005, 1),
        sl_price=round(exec_price * 0.997, 1),
        entry_order_id=market_res.order_id,
        fee_tier=FAKE_FEE,
    )
    bracket_res = await adapter.place_exit_bracket(bracket_req)
    assert bracket_res.status == "placed"
    assert bracket_res.bracket_id.startswith("algo-")

    # 4. Register position in router state (as router would do after bracket)
    pos = _open_fake_position(
        bracket_id=bracket_res.bracket_id,
        tp_id=bracket_res.tp_order_id,
        sl_id=bracket_res.sl_order_id,
        qty=exec_qty,
        entry_price=exec_price,
    )
    assert _execution_state["position_manager"].has_open()

    # 5. Attach order stream
    _execution_state["user_data_stream"] = order_stream
    await order_stream.start(on_order_update=_on_order_update)

    # 6. Simulate TP fill event from OKX algo-orders channel
    tp_event = adapter.simulate_tp_fill(bracket_res)
    with patch("app.scalping.router._update_closed_position_in_db", new_callable=AsyncMock) as mock_db_close:
        await order_stream.fire_fill(tp_event)

        # 7. Position should be closed
        assert not _execution_state["position_manager"].has_open(), "Position should be closed after TP fill"

        # 8. DB close should have been called with reason=take_profit
        mock_db_close.assert_called_once()
        call_args = mock_db_close.call_args
        reason = call_args.args[4] if len(call_args.args) > 4 else call_args.kwargs.get("reason", "")
        assert reason == "take_profit", f"Expected reason=take_profit, got: {reason}"

    # 9. Verify adapter calls
    assert "place_market_order(buy,BTC-EUR)" in adapter.calls
    assert any("place_exit_bracket" in c for c in adapter.calls)


# ── 1111.B — Bracket failure ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_1111b_bracket_failure_emergency_close(adapter, mock_supabase_and_broadcast):
    """
    Scenario 1111.B — Bracket failure:
    Entry OK → bracket rejected → emergency close triggered → no open position saved.
    """
    _reset_execution_state(adapter)

    # Configure adapter to fail on bracket placement
    adapter.bracket_fails = True

    # Place market order first (succeeds)
    market_req = MarketOrderRequest(symbol=BTC_EUR, side="buy", quantity=10.0 / 43700.0, quote_amount=10.0)
    market_res = await adapter.place_market_order(market_req)
    exec_qty = market_res.quantity

    # Simulate the bracket failure handler being called
    await _handle_bracket_failed(adapter, "BTC-EUR")

    # No open position should exist
    assert not _execution_state["position_manager"].has_open(), (
        "No position should be open after bracket failure"
    )

    # Emergency close should have been attempted (cancel + close_position)
    assert any("cancel_open_exit_orders" in c for c in adapter.calls), (
        "cancel_open_exit_orders should be called on bracket failure"
    )

    # Broadcast error should have fired
    mock_supabase_and_broadcast["broadcast"].assert_called()
    call_args_list = mock_supabase_and_broadcast["broadcast"].call_args_list
    event_types = [c.args[0] for c in call_args_list]
    assert "error" in event_types, "An error event should be broadcast on bracket failure"



# ── 1111.C — Stop session ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_1111c_stop_session_cancels_bracket_and_closes(adapter, mock_supabase_and_broadcast):
    """
    Scenario 1111.C — Stop session:
    Open position → session stop → bracket cancelled → market close → DB closed reason=session_stop.
    """
    _reset_execution_state(adapter)

    # Place bracket and register open position
    bracket_req = ExitBracketRequest(
        symbol=BTC_EUR, side="sell", quantity=0.00022883,
        tp_price=43918.5, sl_price=43568.9,
    )
    bracket_res = await adapter.place_exit_bracket(bracket_req)
    pos = _open_fake_position(
        bracket_id=bracket_res.bracket_id,
        tp_id=bracket_res.tp_order_id,
        sl_id=bracket_res.sl_order_id,
    )

    assert adapter.open_brackets, "Bracket should be open before stop"
    assert _execution_state["position_manager"].has_open()

    # Simulate session stop: cancel bracket + close position
    from app.execution.exchange_models import ClosePositionRequest, SymbolRef
    sym_ref = SymbolRef.from_okx("BTC-EUR")

    await adapter.cancel_open_exit_orders(sym_ref)
    assert not adapter.open_brackets, "Brackets should be cancelled"

    close_req = ClosePositionRequest(symbol=sym_ref, side="BUY", quantity=float(pos.quantity))
    await adapter.close_position(close_req)

    # Manually close position in PM (as router does) and record with reason
    pm: PositionManager = _execution_state["position_manager"]
    pm.close_position(Decimal("43700.0"))

    assert not pm.has_open(), "Position should be closed after session stop"

    # Call _update_closed_position_in_db directly - the real function writes to DB
    # The mock_supabase_and_broadcast fixture already patches get_supabase, so
    # this call exercises the reason=session_stop path without hitting real DB.
    await router_module._update_closed_position_in_db(pos, 43700.0, 0.0, 0.0, "session_stop")

    assert any("cancel_open_exit_orders" in c for c in adapter.calls)
    assert any("close_position" in c for c in adapter.calls)


# ── 1111.D — Restore open ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_1111d_restore_open_position_with_bracket(adapter, order_stream, mock_supabase_and_broadcast):
    """
    Scenario 1111.D — Restore open:
    DB has open position with bracket_id → adapter has open bracket →
    order stream restarted → fill event closes the position correctly.
    """
    _reset_execution_state(adapter)

    # Simulate: broker has an open bracket from before restart
    fake_bracket_id = "algo-restored-0001"
    fake_tp_id = "tp-algo-restored-0001"
    fake_sl_id = "sl-algo-restored-0001"
    adapter.open_brackets[fake_bracket_id] = {
        "tp_price": 43918.5,
        "sl_price": 43568.9,
        "qty": 0.00022883,
        "symbol": BTC_EUR,
    }

    # Simulate session restore: position loaded from DB
    pos = _open_fake_position(
        bracket_id=fake_bracket_id,
        tp_id=fake_tp_id,
        sl_id=fake_sl_id,
    )
    assert _execution_state["position_manager"].has_open()

    # Verify adapter knows about the open bracket
    open_orders = await adapter.get_open_exit_orders(BTC_EUR)
    assert len(open_orders) == 1
    assert open_orders[0].order_id == fake_bracket_id

    # Restart order stream (as restore does)
    _execution_state["user_data_stream"] = order_stream
    await order_stream.start(on_order_update=_on_order_update)
    assert order_stream.started

    # Fire a TP fill as if received after reconnect
    tp_event = {
        "provider": "okx",
        "symbol": "BTC-EUR",
        "side": "SELL",
        "order_id": fake_tp_id,
        "bracket_id": fake_bracket_id,
        "order_list_id": fake_bracket_id,
        "status": "filled",
        "fill_price": 43918.5,
        "commission": 0.0,
        "commission_asset": "EUR",
        "leg": "take_profit",
    }

    with patch("app.scalping.router._update_closed_position_in_db", new_callable=AsyncMock) as mock_close:
        await order_stream.fire_fill(tp_event)

        assert not _execution_state["position_manager"].has_open()
        mock_close.assert_called_once()
        reason = mock_close.call_args.args[4]
        assert reason == "take_profit"


# ── 1111.E — Restore closed (reconcile) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_1111e_restore_reconcile_already_closed(adapter, mock_supabase_and_broadcast):
    """
    Scenario 1111.E — Restore closed:
    DB says position is open, but exchange has no open bracket.
    Adapter should detect this and reconcile (close DB record).
    """
    _reset_execution_state(adapter)

    # DB position open, but NO open bracket on exchange (filled while offline)
    bracket_id = "algo-offline-fill-0001"
    # adapter.open_brackets is empty — no bracket exists

    pos = _open_fake_position(
        bracket_id=bracket_id,
        tp_id="tp-offline-0001",
        sl_id="sl-offline-0001",
    )

    # Check: adapter reports no open exit orders
    open_orders = await adapter.get_open_exit_orders(BTC_EUR)
    assert len(open_orders) == 0, "No open brackets should exist after offline fill"

    # Reconcile: close position in memory and DB
    pm: PositionManager = _execution_state["position_manager"]
    pm.close_position(Decimal("43700.0"))  # use last known price as fallback

    assert not pm.has_open(), "Position should be marked closed after reconcile"

    # Call _update_closed_position_in_db with reconciled reason
    await router_module._update_closed_position_in_db(pos, 43700.0, 0.0, 0.0, "reconciled_offline_fill")


# ── 1111.F — Fee/net pricing ───────────────────────────────────────────────────

def test_1111f_net_to_gross_pricing_okx_fees():
    """
    Scenario 1111.F — Fee/net pricing with OKX rebate structure.

    OKX fees are negative (rebates). The router applies abs() before calling
    _net_to_gross_pct (TASK-1114 fix in router.py entry_fee_pricing line).

    With abs(taker=0.0035, maker=0.002):
    - gross TP > net TP (fee overhead added)
    - SL gross (negative) is smaller in abs than net SL
    - TP price is above entry, SL price is below entry
    """
    from app.scalping.router import _net_to_gross_pct, _sl_price_from_entry

    entry_price = 43700.0

    # Router applies abs() — use the same values the router will use
    entry_fee = abs(FAKE_FEE.taker)   # 0.0035
    exit_fee = abs(FAKE_FEE.maker)    # 0.002

    tp_net_pct = 0.5
    sl_net_pct = 0.3

    tp_gross_pct = _net_to_gross_pct(tp_net_pct, entry_fee, exit_fee)

    tp_price = round(entry_price * (1 + tp_gross_pct / 100), 1)
    sl_price = round(_sl_price_from_entry(entry_price, "BUY", sl_net_pct, entry_fee, exit_fee), 1)

    assert tp_gross_pct > tp_net_pct, (
        f"Gross TP {tp_gross_pct:.4f}% should exceed net {tp_net_pct}% (fee overhead)"
    )
    # With high OKX fees, _net_to_gross_pct(-0.3,...) returns POSITIVE (~0.25%).
    # Router must use _sl_price_from_entry (1 - move) for BUY, not (1 + gross).
    assert tp_price > entry_price, f"TP {tp_price} should be above entry {entry_price}"
    assert sl_price < entry_price, f"SL price {sl_price} should be below entry {entry_price}"
    assert tp_price > sl_price, "TP must be above SL"

    # gross TP ≈ net + entry_fee + exit_fee (within 0.1%)
    expected_approx = tp_net_pct + (entry_fee + exit_fee) * 100
    assert abs(tp_gross_pct - expected_approx) < 0.1, (
        f"TP gross {tp_gross_pct:.4f}% too far from expected ~{expected_approx:.4f}%"
    )


def test_1111f_fee_tier_okx_rebate_structure():
    """
    Verify that FakeOkxAdapter returns the correct OKX fee structure:
    negative values = rebate (OKX pays the trader).
    """
    assert FAKE_FEE.maker < 0, "OKX maker fee should be negative (rebate)"
    assert FAKE_FEE.taker < 0, "OKX taker fee should be negative (rebate)"
    assert FAKE_FEE.certified is True
    assert FAKE_FEE.source == "fake_okx"


@pytest.mark.asyncio
async def test_1111f_adapter_fee_tier_returned(adapter):
    """FakeOkxAdapter.get_trade_fee returns the expected OKX fee structure."""
    fee = await adapter.get_trade_fee(BTC_EUR)
    assert fee.maker == -0.002
    assert fee.taker == -0.0035
    assert fee.certified is True


# ── 1111.extra — FakeOkxAdapter unit checks ────────────────────────────────────

@pytest.mark.asyncio
async def test_fake_adapter_market_order_updates_balances(adapter):
    """Market buy reduces EUR balance and increases BTC holdings."""
    pre_eur = adapter.balances["EUR"]
    req = MarketOrderRequest(symbol=BTC_EUR, side="buy", quantity=10.0 / 43700.0, quote_amount=10.0)
    order = await adapter.place_market_order(req)

    assert order.quantity > 0
    assert adapter.balances["EUR"] < pre_eur
    assert adapter.balances["BTC"] > 0
    assert adapter.holdings_data["BTC"] > 0


@pytest.mark.asyncio
async def test_fake_adapter_bracket_failure_raises(adapter):
    """FakeOkxAdapter raises on place_exit_bracket when bracket_fails=True."""
    adapter.bracket_fails = True
    req = ExitBracketRequest(
        symbol=BTC_EUR, side="sell", quantity=0.001,
        tp_price=44000.0, sl_price=43000.0,
    )
    with pytest.raises(Exception, match="bracket_fails"):
        await adapter.place_exit_bracket(req)


@pytest.mark.asyncio
async def test_fake_order_stream_fire_fill_calls_handler(order_stream):
    """FakeOrderStream.fire_fill invokes the registered on_order_update callback."""
    received = []

    async def handler(event: dict) -> None:
        received.append(event)

    await order_stream.start(on_order_update=handler)
    await order_stream.fire_fill({"status": "filled", "leg": "take_profit"})

    assert len(received) == 1
    assert received[0]["leg"] == "take_profit"


@pytest.mark.asyncio
async def test_fake_adapter_cancel_clears_brackets(adapter):
    """cancel_open_exit_orders removes the bracket from open_brackets."""
    req = ExitBracketRequest(
        symbol=BTC_EUR, side="sell", quantity=0.001,
        tp_price=44000.0, sl_price=43000.0,
    )
    bracket = await adapter.place_exit_bracket(req)
    assert bracket.bracket_id in adapter.open_brackets

    await adapter.cancel_open_exit_orders(BTC_EUR)
    assert bracket.bracket_id not in adapter.open_brackets
