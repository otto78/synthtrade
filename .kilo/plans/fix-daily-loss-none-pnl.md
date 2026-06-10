# Fix TypeError in _check_daily_loss()

## Problem
`router.py:428` crashes with `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'` because some entries in `_execution_state["trade_history"]` have `pnl=None` (e.g., open positions or trades where PnL hasn't been calculated yet).

## Root Cause
The `sum()` generator expression at line 428 doesn't guard against `None` values in `t["pnl"]`.

## Fix
Update `_check_daily_loss()` to treat `None` PnL as `0.0`:

```python
total_pnl = sum(t.get("pnl") or 0.0 for t in _execution_state["trade_history"] if t["timestamp"].startswith(now_str))
```

This ensures entries with `pnl=None` contribute 0 to the daily loss calculation, which is the correct behavior for trades without realized PnL.

## File
- `synthtrade/backend/app/scalping/router.py:428`
