import pytest
from app.ai.eval_parser import parse_eval_result, EvalParseError


def test_parse_valid_json():
    raw = '{"score": 0.8, "verdict": "PROMOTE", "reasoning": "Good metrics", "confidence": 0.9}'
    result = parse_eval_result(raw, strategy_id="s1", model_used="model-a")
    assert result.score == 0.8
    assert result.verdict == "PROMOTE"
    assert result.reasoning == "Good metrics"
    assert result.model_used == "model-a"


def test_parse_extracts_json_from_markdown():
    raw = '```json\n{"score": 0.5, "verdict": "HOLD", "reasoning": "Average", "confidence": 0.7}\n```'
    result = parse_eval_result(raw, strategy_id="s1", model_used="m")
    assert result.verdict == "HOLD"


def test_score_clamped_above_1(caplog):
    raw = '{"score": 1.5, "verdict": "PROMOTE", "reasoning": "ok", "confidence": 0.8}'
    result = parse_eval_result(raw, strategy_id="s1", model_used="m")
    assert result.score == 1.0


def test_score_clamped_below_0(caplog):
    raw = '{"score": -0.3, "verdict": "DEMOTE", "reasoning": "bad", "confidence": 0.6}'
    result = parse_eval_result(raw, strategy_id="s1", model_used="m")
    assert result.score == 0.0


def test_invalid_verdict_raises():
    raw = '{"score": 0.5, "verdict": "UNKNOWN", "reasoning": "ok", "confidence": 0.7}'
    with pytest.raises(EvalParseError, match="verdict"):
        parse_eval_result(raw, strategy_id="s1", model_used="m")


def test_missing_reasoning_raises():
    raw = '{"score": 0.5, "verdict": "HOLD", "confidence": 0.7}'
    with pytest.raises(EvalParseError, match="reasoning"):
        parse_eval_result(raw, strategy_id="s1", model_used="m")


def test_empty_reasoning_raises():
    raw = '{"score": 0.5, "verdict": "HOLD", "reasoning": "", "confidence": 0.7}'
    with pytest.raises(EvalParseError, match="reasoning"):
        parse_eval_result(raw, strategy_id="s1", model_used="m")


def test_malformed_json_raises_eval_parse_error():
    with pytest.raises(EvalParseError, match="JSON"):
        parse_eval_result("not json at all", strategy_id="s1", model_used="m")
