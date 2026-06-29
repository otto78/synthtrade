"""Test unitari per DecisionContextExtractor."""

import pytest
from datetime import datetime
from app.core.decision_context import DecisionContext, extract_decision_context, extract_from_pipeline_log


def test_extract_decision_context_basic():
    """Test estrazione contesto base con campi obbligatori."""
    ctx = extract_decision_context(
        session_id="123",
        symbol="BTCUSDT",
        regime="ranging",
        strategy_type="rsi_bollinger"
    )
    
    assert ctx.session_id == "123"
    assert ctx.symbol == "BTCUSDT"
    assert ctx.regime == "ranging"
    assert ctx.strategy_type == "rsi_bollinger"
    assert ctx.decided_at is not None


def test_extract_decision_context_full():
    """Test estrazione contesto completo con tutti i campi."""
    ctx = extract_decision_context(
        session_id="123",
        symbol="BTCUSDT",
        regime="ranging",
        strategy_type="rsi_bollinger",
        tech_signal="BUY",
        tech_confidence=0.85,
        intel_score=0.75,
        intel_bias="bullish",
        trend_direction="converging",
        trend_value=0.5,
        decision_type="execute",
        decision_reason="Tutti i criteri soddisfatti"
    )
    
    assert ctx.tech_signal == "BUY"
    assert ctx.tech_confidence == 0.85
    assert ctx.intel_score == 0.75
    assert ctx.intel_bias == "bullish"
    assert ctx.trend_direction == "converging"
    assert ctx.trend_value == 0.5
    assert ctx.decision_type == "execute"
    assert ctx.decision_reason == "Tutti i criteri soddisfatti"


def test_extract_decision_context_missing_required():
    """Test che manca campo obbligatorio solleva ValueError."""
    with pytest.raises(ValueError, match="Campo obbligatorio mancante"):
        extract_decision_context(
            session_id="123",
            symbol="BTCUSDT",
            regime="ranging"
            # strategy_type mancante
        )


def test_extract_decision_context_type_conversion():
    """Test conversione tipi automatica."""
    ctx = extract_decision_context(
        session_id=123,  # int -> str
        symbol=456,      # int -> str
        regime="ranging",
        strategy_type="rsi_bollinger"
    )
    
    assert isinstance(ctx.session_id, str)
    assert isinstance(ctx.symbol, str)
    assert ctx.session_id == "123"
    assert ctx.symbol == "456"


def test_decision_context_to_dict():
    """Test conversione a dict."""
    ctx = DecisionContext(
        session_id="123",
        symbol="BTCUSDT",
        regime="ranging",
        strategy_type="rsi_bollinger",
        tech_signal="BUY"
    )
    
    result = ctx.to_dict()
    assert result['session_id'] == "123"
    assert result['symbol'] == "BTCUSDT"
    assert result['tech_signal'] == "BUY"


def test_decision_context_to_db_dict():
    """Test conversione a dict per DB (rimuove None)."""
    ctx = DecisionContext(
        session_id="123",
        symbol="BTCUSDT",
        regime="ranging",
        strategy_type="rsi_bollinger",
        tech_signal="BUY",
        tech_confidence=None,  # deve essere rimosso
        intel_score=0.75
    )
    
    result = ctx.to_db_dict()
    assert 'tech_confidence' not in result
    assert 'intel_score' in result
    assert result['intel_score'] == 0.75


def test_decision_context_to_db_dict_datetime():
    """Test conversione datetime a stringa ISO."""
    dt = datetime(2026, 6, 29, 12, 0, 0)
    ctx = DecisionContext(
        session_id="123",
        symbol="BTCUSDT",
        regime="ranging",
        strategy_type="rsi_bollinger",
        decided_at=dt
    )
    
    result = ctx.to_db_dict()
    assert result['decided_at'] == dt.isoformat()


def test_extract_from_pipeline_log_success():
    """Test estrazione da log PIPELINE con successo."""
    log_message = "PIPELINE: regime=ranging strategy=rsi_bollinger vol_anomaly=True tradeable=True"
    ctx = extract_from_pipeline_log(log_message, "123", "BTCUSDT")
    
    assert ctx is not None
    assert ctx.session_id == "123"
    assert ctx.symbol == "BTCUSDT"
    assert ctx.regime == "ranging"
    assert ctx.strategy_type == "rsi_bollinger"
    assert ctx.decision_type == "execute"


def test_extract_from_pipeline_log_rejected():
    """Test estrazione da log PIPELINE con tradeable=False."""
    log_message = "PIPELINE: regime=ranging strategy=rsi_bollinger vol_anomaly=True tradeable=False"
    ctx = extract_from_pipeline_log(log_message, "123", "BTCUSDT")
    
    assert ctx is not None
    assert ctx.decision_type == "rejected"


def test_extract_from_pipeline_log_invalid():
    """Test estrazione da log PIPELINE con formato invalido."""
    log_message = "PIPELINE: formato invalido senza regime o strategy"
    ctx = extract_from_pipeline_log(log_message, "123", "BTCUSDT")
    
    assert ctx is None


def test_extract_decision_context_defaults():
    """Test che campi opzionali abbiano default None."""
    ctx = extract_decision_context(
        session_id="123",
        symbol="BTCUSDT",
        regime="ranging",
        strategy_type="rsi_bollinger"
    )
    
    assert ctx.tech_signal is None
    assert ctx.tech_confidence is None
    assert ctx.intel_score is None
    assert ctx.intel_bias is None
    assert ctx.trend_direction is None
    assert ctx.trend_value is None
    assert ctx.decision_type is None
    assert ctx.decision_reason is None
    assert ctx.trade_id is None