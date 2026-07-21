"""Market processors — re-export module for backward compatibility.

The actual implementations have been split into:
  - candle_processor.py  (_candle_processor)
  - trade_processor.py   (_trade_processor)
  - intel_processor.py   (_intelligence_processor, restore_mode_post_start)

All symbols are re-exported here so existing imports continue to work.
"""
from app.scalping.candle_processor import _candle_processor  # noqa: F401
from app.scalping.trade_processor import _trade_processor  # noqa: F401
from app.scalping.intel_processor import _intelligence_processor, restore_mode_post_start  # noqa: F401
