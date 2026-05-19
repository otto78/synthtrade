import pytest
from app.execution.risk_manager import RiskConfig
from app.config import Settings

def test_risk_config_from_settings():
    settings = Settings()
    # Mock settings values for predictability
    settings.MAX_CONCURRENT_POSITIONS = 5
    settings.MAX_EXPOSURE_PER_SYMBOL_PCT = 0.2
    settings.MAX_DRAWDOWN_PCT = 10.0
    settings.DEFAULT_POSITION_SIZE_PCT = 0.01
    settings.DEFAULT_STOP_LOSS_PCT = 0.03
    settings.DEFAULT_TAKE_PROFIT_PCT = 0.05
    
    config = RiskConfig.from_settings(settings)
    
    assert config.max_concurrent_positions == 5
    assert config.max_exposure_per_symbol_pct == 0.2
    assert config.max_drawdown_pct == 10.0
    assert config.default_position_size_pct == 0.01
    assert config.default_stop_loss_pct == 0.03
    assert config.default_take_profit_pct == 0.05

def test_risk_config_injectable_in_dependencies():
    from app.dependencies import get_risk_config
    # This should return a RiskConfig instance
    config = get_risk_config()
    assert isinstance(config, RiskConfig)
