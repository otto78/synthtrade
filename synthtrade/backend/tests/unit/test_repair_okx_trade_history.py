"""Unit tests for the offline OCO history repair job (no DB/OKX access)."""
from __future__ import annotations

import importlib.util
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "repair_okx_trade_history.py"
_SPEC = importlib.util.spec_from_file_location("repair_okx_trade_history", _SCRIPT)
assert _SPEC and _SPEC.loader
repair = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(repair)


def test_repair_values_uses_verified_fill_and_stored_fees():
    row = {
        "entry_price": 100.0, "quantity": 2.0, "side": "BUY",
        "entry_commission": 0.1, "exit_commission": 0.2,
    }
    match = {
        "fill_price": 110.0, "fill_time": "2026-08-04T09:18:04+00:00",
        "reason": "stop_loss", "source": "oco_verified_fill", "exit_order_id": "child-1",
    }
    result = repair._repair_values(row, match, 0.001)
    assert result["exit_price"] == 110.0
    assert result["pnl"] == 19.7
    assert result["fee_source"] == "stored"
    assert result["exit_time"] == match["fill_time"]


def test_repair_rejects_row_without_oco_identity():
    assert repair._validate_row({"symbol": "BTC-EUR", "entry_price": 1, "quantity": 1}) == "skip_missing_oco_id"
