# Fix: Bracket OCO 51020 + Emergency Close Side Inversion

## Root Causes

### Bug 1: `51020` — OCO exit order fails with "minimum order amount"

**Root cause:** `_direct_place_exit_bracket()` in `okx_exchange.py:1129-1141` sends the OCO body with `"sz": str(quantity)` but **no `tgtCcy`**. Per OKX API docs, the default for market BUY orders is `tgtCcy=quote_ccy` (sz = EUR amount). Our `sz=0.001739` was interpreted as **0.001739 EUR**, far below any minimum.

**Fix:** Add `"tgtCcy": "base_ccy"` to the OCO body so `sz` is always interpreted as base currency (BTC). This applies to both BUY (short close) and SELL (long close) — for SELL the default is already `base_ccy`, but adding it explicitly is safer.

**File:** `synthtrade/backend/app/execution/okx_exchange.py:1129-1141`

### Bug 2: `51008` — Emergency close places SELL instead of BUY

**Root cause:** `candle_processor.py:614` passes `side="buy"` to `ClosePositionRequest`. But `close_position()` in `okx_exchange.py:950-954` does `opp_side = "sell" if request.side == "buy" else "buy"` — it interprets `side="buy"` as "closing a long position" and reverses to SELL. For shorts, we need `side="sell"` so `close_position()` reverses to BUY.

**Fix:** Change `side="buy"` to `side="sell"` at `candle_processor.py:614`.

**File:** `synthtrade/backend/app/scalping/candle_processor.py:614`

## Changes

### 1. `okx_exchange.py` — `_direct_place_exit_bracket()`

Add `"tgtCcy": "base_ccy"` to the OCO body dict.

```python
body = {
    "instId": symbol.okx,
    "tdMode": td_mode,
    "side": side,
    "ordType": "oco",
    "sz": str(quantity),
    "tgtCcy": "base_ccy",          # ← ADD: sz must be base qty, not quote
    "tpTriggerPx": str(tp_price),
    "tpOrdPx": "-1",
    "slTriggerPx": str(sl_price),
    "slOrdPx": "-1",
    "tpTriggerPxType": "last",
    "slTriggerPxType": "last",
}
```

### 2. `candle_processor.py` — emergency close for short

Change line 614 from `side="buy"` to `side="sell"`:

```python
close_req = ClosePositionRequest(
    symbol=_close_sym_ref,
    side="sell",  # SHORT position: close_position() reverses to "buy"
    quantity=exec_qty,
)
```

## Verification

1. Run `ruff check` on both files
2. Run existing unit tests: `pytest synthtrade/backend/tests/unit/test_task_1224.py -v`
3. Verify bracket OCO succeeds in demo by starting a short session
4. Verify emergency close places correct BUY order (not SELL)
