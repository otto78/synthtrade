"""
Tests for TASK-015: Refactor config.py (Pydantic Settings)
"""

import os
import pytest
from synthtrade.backend.app.config import Settings, settings

def test_settings_default_values():
    s = Settings(_env_file=None, TRADING_MODE='test')  # type: ignore[call-arg]
    assert s.BINANCE_TESTNET is True
    assert s.APP_PASSWORD == "changeme"
    assert s.JWT_EXPIRE_MINUTES == 1440
    assert s.LOG_LEVEL == "INFO"

def test_binance_base_url_logic():
    # BINANCE_TESTNET is now a computed_field derived from TRADING_MODE
    s_testnet = Settings(TRADING_MODE='test')
    assert s_testnet.binance_base_url == "https://testnet.binance.vision"
    assert s_testnet.binance_ws_base_url == "wss://stream.testnet.binance.vision/ws"

    s_mainnet = Settings(TRADING_MODE='live')
    assert s_mainnet.binance_base_url == "https://api.binance.com"
    assert s_mainnet.binance_ws_base_url == "wss://stream.binance.com:9443/ws"

def test_cors_origins_list():
    s = Settings(CORS_ORIGINS="http://localhost:4208,http://example.com")
    assert s.cors_origins_list == ["http://localhost:4208", "http://example.com"]

def test_ai_cascade_models_list():
    s = Settings(AI_CASCADE_MODELS="model1, model2, model3")
    assert s.ai_cascade_models_list == ["model1", "model2", "model3"]

def test_settings_validation():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(AI_CASCADE_TIMEOUT="not-a-number")  # type: ignore[arg-type]

def test_singleton_instance():
    assert isinstance(settings, Settings)
