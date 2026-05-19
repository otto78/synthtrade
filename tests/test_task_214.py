import pytest
from unittest.mock import MagicMock
from app.execution.registry import StrategyRegistry
import os

def test_registry_singleton():
    reg1 = StrategyRegistry()
    reg2 = StrategyRegistry()
    assert reg1 is reg2

def test_register_and_get_strategy():
    registry = StrategyRegistry()
    mock_fn = MagicMock()
    registry.register("test_strat", mock_fn)
    assert registry.get("test_strat") == mock_fn

def test_load_plugins_from_module(tmp_path):
    # Create a temporary plugin file
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "my_plugin.py"
    plugin_file.write_text("""
def signal_custom(df, params):
    return 1
""")
    
    # Add to sys.path for importlib to find it
    import sys
    sys.path.append(str(tmp_path))
    
    registry = StrategyRegistry()
    registry.load_from_module("plugins.my_plugin")
    
    # We expect signal_custom to be registered if it followed a naming convention 
    # OR if there was a registration call in the plugin.
    # Let's assume a naming convention for now: functions starting with 'signal_' are registered.
    assert registry.get("custom") is not None
    assert registry.get("custom")(None, None) == 1
    
    sys.path.remove(str(tmp_path))

def test_signal_map_integration():
    # Ensure our existing signals are registered by default or during init
    registry = StrategyRegistry()
    assert registry.get("trend_ema") is not None
    assert registry.get("mean_reversion_rsi") is not None
    assert registry.get("breakout_bb") is not None
