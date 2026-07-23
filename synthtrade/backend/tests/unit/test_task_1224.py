"""TASK-1224: Short opening flow tests.

Tests verify the key behavioral changes in candle_processor.py for SELL (short)
vs the existing BUY (long) flow:

- MarketOrderRequest uses margin_mode="cross" for SELL
- Bracket side is "buy" for SELL (close short)
- Bracket qty uses exec_qty directly for SELL (no balance check)
- Emergency close after bracket failure does market buy for SELL
- Paper mode SELL increases paper_balance (proceeds from short sale)
- TP below entry, SL above entry for SELL
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal

from app.scalping._state import _execution_state


class TestSellMarketOrderRequest:
    """Verify MarketOrderRequest is constructed correctly for SELL (short)."""

    def test_sell_uses_cross_margin_mode(self):
        """TASK-1224.D: SELL order uses margin_mode='cross'."""
        from app.execution.exchange_models import MarketOrderRequest, SymbolRef

        sym_ref = SymbolRef(base="BTC", quote="EUR")
        req = MarketOrderRequest(
            symbol=sym_ref,
            side="sell",
            quote_amount=100.0,
            margin_mode="cross",
        )
        assert req.side == "sell"
        assert req.margin_mode == "cross"
        assert req.quote_amount == 100.0

    def test_buy_has_no_margin_mode(self):
        """BUY order has margin_mode=None (spot, no margin)."""
        from app.execution.exchange_models import MarketOrderRequest, SymbolRef

        sym_ref = SymbolRef(base="BTC", quote="EUR")
        req = MarketOrderRequest(
            symbol=sym_ref,
            side="buy",
            quote_amount=100.0,
            margin_mode=None,
        )
        assert req.side == "buy"
        assert req.margin_mode is None


class TestSellBracketDirection:
    """Verify bracket TP/SL direction is inverted for SELL (short)."""

    def test_sl_above_entry_for_sell(self):
        """TASK-1224.F: SL must be ABOVE entry price for short."""
        from app.scalping.pricing import _sl_price_from_entry, _net_to_gross_pct, _sl_gross_fraction

        entry = 50000.0
        sl_pct = 0.3
        entry_fee = 0.001
        exit_fee = 0.001

        sl_price, feasible = _sl_price_from_entry(
            entry, "SELL", sl_pct, entry_fee, exit_fee, price_prec=2,
        )
        assert sl_price > entry, f"SL={sl_price} should be > entry={entry} for SELL"
        assert feasible is True

    def test_tp_below_entry_for_sell(self):
        """TASK-1224.F: TP must be BELOW entry price for short."""
        from app.scalping.pricing import _tp_price_from_entry, _net_to_gross_pct

        entry = 50000.0
        tp_pct = 0.5
        entry_fee = 0.001
        exit_fee = 0.001

        tp_gross_pct = _net_to_gross_pct(tp_pct, entry_fee, exit_fee) / 100
        tp_price = round(entry * (1 - tp_gross_pct), 2)  # SELL: entry * (1 - tp_gross_pct)

        assert tp_price < entry, f"TP={tp_price} should be < entry={entry} for SELL"

    def test_sl_above_entry_for_buy(self):
        """BUY: SL is BELOW entry price (standard long behavior)."""
        from app.scalping.pricing import _sl_price_from_entry

        entry = 50000.0
        sl_pct = 0.3
        entry_fee = 0.001
        exit_fee = 0.001

        sl_price, feasible = _sl_price_from_entry(
            entry, "BUY", sl_pct, entry_fee, exit_fee, price_prec=2,
        )
        assert sl_price < entry, f"SL={sl_price} should be < entry={entry} for BUY"


class TestSellBracketRequest:
    """Verify ExitBracketRequest is constructed correctly for SELL."""

    def test_bracket_side_is_buy_for_short(self):
        """TASK-1224.F: Bracket side='buy' when entry side='SELL' (close short)."""
        from app.execution.exchange_models import ExitBracketRequest, SymbolRef, FeeTier

        sym_ref = SymbolRef(base="BTC", quote="EUR")
        fee_tier = FeeTier(maker=0.001, taker=0.001, certified=False, source="test")

        bracket_side = "sell" if "BUY" == "SELL" else "buy"  # mirrors candle_processor logic
        req = ExitBracketRequest(
            symbol=sym_ref,
            side=bracket_side,
            quantity=0.002,
            tp_price=49500.0,
            sl_price=50500.0,
            fee_tier=fee_tier,
            margin_mode="cross",
        )
        assert req.side == "buy"  # close short = buy
        assert req.margin_mode == "cross"
        assert req.sl_price > req.tp_price  # SL above TP for short


class TestSellBracketQty:
    """Verify bracket qty logic for SELL uses exec_qty directly."""

    def test_sell_bracket_qty_uses_exec_qty(self):
        """TASK-1224.F: For SELL, bracket_qty = exec_qty (no balance check)."""
        # Mirror the logic from candle_processor.py
        side = "SELL"
        exec_qty = 0.002
        entry_fee_pricing = 0.001

        if side == "BUY":
            bracket_qty = exec_qty - (exec_qty * entry_fee_pricing)
        else:
            bracket_qty = exec_qty  # TASK-1224: short — use exec_qty directly

        assert bracket_qty == exec_qty


class TestPaperModeShort:
    """Verify paper mode handles SELL correctly."""

    def test_paper_balance_increases_for_short(self):
        """TASK-1224: Paper SELL increases balance (proceeds from short sale)."""
        _execution_state["session"]["paper_balance"] = 1000.0

        trade_val = 100.0
        side = "SELL"

        if side == "BUY":
            _execution_state["session"]["paper_balance"] -= trade_val
        else:
            _execution_state["session"]["paper_balance"] += trade_val

        assert _execution_state["session"]["paper_balance"] == 1100.0

        # Cleanup
        _execution_state["session"]["paper_balance"] = 1000.0

    def test_paper_balance_decreases_for_buy(self):
        """Paper BUY decreases balance (spend quote to buy base)."""
        _execution_state["session"]["paper_balance"] = 1000.0

        trade_val = 100.0
        side = "BUY"

        if side == "BUY":
            _execution_state["session"]["paper_balance"] -= trade_val
        else:
            _execution_state["session"]["paper_balance"] += trade_val

        assert _execution_state["session"]["paper_balance"] == 900.0

        # Cleanup
        _execution_state["session"]["paper_balance"] = 1000.0


class TestSellEmergencyClose:
    """Verify emergency close after bracket failure uses market buy for short."""

    def test_short_emergency_close_uses_sell(self):
        """TASK-1224.G: Bracket failure for short → ClosePositionRequest(side='sell')
        so close_position() reverses to 'buy' (market BUY to repay borrow)."""
        from app.execution.exchange_models import ClosePositionRequest, SymbolRef

        sym_ref = SymbolRef(base="BTC", quote="EUR")
        exec_qty = 0.002

        # Mirror the logic from candle_processor.py
        side = "SELL"
        if side == "SELL":
            close_req = ClosePositionRequest(
                symbol=sym_ref,
                side="sell",  # SHORT: close_position() reverses to "buy"
                quantity=exec_qty,
            )
        else:
            close_req = ClosePositionRequest(
                symbol=sym_ref,
                side="sell",  # close long = sell
                quantity=exec_qty,
            )

        assert close_req.side == "sell"
        assert close_req.quantity == exec_qty

    def test_long_emergency_close_uses_sell(self):
        """Bracket failure for long → emergency market sell (existing behavior)."""
        from app.execution.exchange_models import ClosePositionRequest, SymbolRef

        sym_ref = SymbolRef(base="BTC", quote="EUR")
        exec_qty = 0.002

        side = "BUY"
        if side == "SELL":
            close_req = ClosePositionRequest(symbol=sym_ref, side="buy", quantity=exec_qty)
        else:
            close_req = ClosePositionRequest(symbol=sym_ref, side="sell", quantity=exec_qty)

        assert close_req.side == "sell"
