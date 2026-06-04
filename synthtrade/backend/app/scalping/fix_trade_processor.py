#!/usr/bin/env python3
"""Fix _trade_processor in router.py"""

filepath = "router.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '                    logger.warning(f"Execution loop processing error: {e}")\n        """Consume trade_queue and broadcast + update PnL."""\n        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():'

new = '                    logger.warning(f"Execution loop processing error: {e}")\n\n    async def _trade_processor():\n        """Consume trade_queue and broadcast + update PnL."""\n        while _execution_state["session"]["status"] != "idle" and not client._stop_event.is_set():'

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK - Fixed _trade_processor definition")
else:
    print("ERROR - Pattern not found")
