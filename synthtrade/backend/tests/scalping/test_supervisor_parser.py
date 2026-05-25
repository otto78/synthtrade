"""Test per supervisor parser e modelli."""

import pytest
from app.ai.eval_parser import parse_supervisor_decision, EvalParseError
from app.scalping.models.supervisor import SupervisorDecision


class TestSupervisorParser:
    def test_parse_valid_decision(self):
        raw = '''
        {
            "action": "no_action",
            "reason": "market conditions normal",
            "confidence": 0.75,
            "market_bias": "neutral",
            "primary_signal": "funding_rate"
        }
        '''
        result = parse_supervisor_decision(raw)
        assert result.action == "no_action"
        assert result.confidence == 0.75
        assert result.market_bias == "neutral"

    def test_parse_update_params(self):
        raw = '''
        ```json
        {
            "action": "update_params",
            "reason": "ATR increased, adjusting SL",
            "confidence": 0.9,
            "market_bias": "bullish",
            "primary_signal": "cvd",
            "new_params": {"atr_multiplier": 2.0}
        }
        ```
        '''
        result = parse_supervisor_decision(raw)
        assert result.action == "update_params"
        assert result.new_params == {"atr_multiplier": 2.0}

    def test_parse_change_strategy(self):
        raw = '{"action": "change_strategy", "reason": "regime shift", "confidence": 0.8, "new_strategy": "rsi_bollinger"}'
        result = parse_supervisor_decision(raw)
        assert result.new_strategy == "rsi_bollinger"

    def test_parse_pause_trading(self):
        raw = '{"action": "pause_trading", "reason": "high volatility", "confidence": 0.95}'
        result = parse_supervisor_decision(raw)
        assert result.action == "pause_trading"

    def test_invalid_action_raises(self):
        raw = '{"action": "invalid_action", "reason": "test", "confidence": 0.5}'
        with pytest.raises(EvalParseError):
            parse_supervisor_decision(raw)

    def test_invalid_json_raises(self):
        raw = 'not json at all'
        with pytest.raises(EvalParseError):
            parse_supervisor_decision(raw)


class TestSupervisorDecision:
    def test_valid_decision(self):
        d = SupervisorDecision(
            action="no_action",
            reason="test",
            confidence=0.5,
            market_bias="neutral",
        )
        assert d.action == "no_action"

    def test_frozen_model(self):
        d = SupervisorDecision(
            action="no_action",
            reason="test",
            confidence=0.5,
        )
        from pydantic_core import ValidationError
        with pytest.raises(ValidationError):
            d.action = "update_params"