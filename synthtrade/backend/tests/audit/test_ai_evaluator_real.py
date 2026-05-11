"""
TASK-AUDIT-003 — Test AI Evaluator reale

Verifica che il model_client si connetta davvero a OpenRouter e riceva
una risposta JSON valida con score, verdict, reasoning.

Richiede AI_API_KEY configurata in synthtrade/backend/.env

Esecuzione:
    cd synthtrade/backend
    python -m pytest tests/audit/test_ai_evaluator_real.py -v -s -m "real_api"
"""

import os
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.ai.eval_parser import parse_eval_result, EvalParseError
from app.ai.prompt_builder import build_system_prompt
from app.ai.schemas import EvalResult


# ─── Test con mock (sempre eseguibili) ───────────────────────────────────────

def test_eval_parser_accepts_valid_json():
    """
    AUDIT: Il parser accetta correttamente il JSON strutturato dell'AI.
    Verifica che il formato di risposta atteso sia parsabile.
    """
    valid_json = json.dumps({
        "score": 0.72,
        "verdict": "PROMOTE",
        "reasoning": "Strategia con buon Sharpe ratio e drawdown contenuto.",
        "confidence": 0.85,
    })

    result = parse_eval_result(valid_json, "test_strat_id", "google/gemini-2.0-flash")
    assert result.score == 0.72
    assert result.verdict == "PROMOTE"
    assert result.strategy_id == "test_strat_id"
    assert result.model_used == "google/gemini-2.0-flash"
    print(f"\n   ✅ Parser OK: score={result.score} verdict={result.verdict} model={result.model_used}")



def test_eval_parser_rejects_invalid_verdict():
    """AUDIT: Il parser rifiuta verdetti non attesi."""
    invalid_json = json.dumps({
        "score": 0.5,
        "verdict": "MAYBE",  # Non valido
        "reasoning": "test",
        "confidence": 0.5,
    })
    with pytest.raises(EvalParseError):
        parse_eval_result(invalid_json, "test_id", "model")


def test_eval_parser_handles_markdown_wrapped_json():
    """AUDIT: Il parser gestisce JSON avvolto in markdown (problema comune dei LLM)."""
    wrapped = '```json\n{"score": 0.6, "verdict": "HOLD", "reasoning": "ok", "confidence": 0.7}\n```'
    result = parse_eval_result(wrapped, "test_id", "model")
    assert result.score == 0.6
    assert result.verdict == "HOLD"


def test_system_prompt_is_not_empty():
    """AUDIT: Il system prompt contiene istruzioni per output JSON strutturato."""
    prompt = build_system_prompt()
    assert len(prompt) > 50, "System prompt troppo corto"
    assert "JSON" in prompt, "System prompt non contiene istruzione JSON"
    assert any(word in prompt for word in ["score", "verdict", "PROMOTE", "DEMOTE"]), (
        "System prompt non contiene i campi richiesti"
    )
    print(f"\n   ✅ System prompt: {len(prompt)} chars")
    print(f"   Preview: {prompt[:200]}")


@pytest.mark.asyncio
async def test_model_client_called_with_correct_structure():
    """
    AUDIT: Verifica che model_client invii la richiesta nel formato corretto
    a OpenRouter (mock — non chiama l'API reale).
    """
    import httpx
    from app.ai.model_client import ModelClient

    client = ModelClient(
        api_key="test-key",
        api_base_url="https://openrouter.ai/api/v1",
        cascade_models=["google/gemini-2.0-flash-exp:free"],
        fallback_model="anthropic/claude-haiku-4",
        timeout=30.0, max_retries=1, backoff_base=2.0
    )

    mock_response_data = {
        "choices": [{"message": {"content": '{"score": 0.8, "verdict": "PROMOTE", "reasoning": "Good strategy", "confidence": 0.9}'}}],
        "model": "google/gemini-2.0-flash-exp:free",
        "usage": {"total_tokens": 150},
    }

    with patch("httpx.AsyncClient") as mock_http_class:
        mock_http = MagicMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_http_class.return_value = mock_http

        response = await client.call_with_fallback("system_prompt", "user_prompt")

    # Verifica che il POST sia stato fatto con i parametri giusti
    call_kwargs = mock_http.post.call_args
    assert call_kwargs is not None, "Nessuna chiamata HTTP effettuata"

    body = call_kwargs.kwargs.get("json", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
    assert "messages" in body, "Body non contiene 'messages'"
    assert body["messages"][0]["role"] == "system", "Primo messaggio non è system"
    assert body["messages"][1]["role"] == "user", "Secondo messaggio non è user"
    assert "model" in body, "Body non contiene 'model'"

    assert response.content == '{"score": 0.8, "verdict": "PROMOTE", "reasoning": "Good strategy", "confidence": 0.9}'
    print(f"\n   ✅ HTTP call structure: OK")
    print(f"   Model: {body['model']}")
    print(f"   Messages: system + user")


# ─── Test con API reale (opzionale, richiede AI_API_KEY) ─────────────────────

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("AI_API_KEY") and not os.environ.get("OPENROUTER_API_KEY"),
    reason="AI_API_KEY o OPENROUTER_API_KEY non configurata — skip test real API"
)
async def test_model_client_real_api_call():
    """
    AUDIT: Verifica connessione reale a OpenRouter.
    
    SKIP se AI_API_KEY non è configurata.
    Esegui con: python -m pytest tests/audit/test_ai_evaluator_real.py::test_model_client_real_api_call -v -s
    """
    from app.ai.model_client import ModelClient
    from app.config import settings

    api_key = settings.AI_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        pytest.skip("Nessuna API key disponibile")

    client = ModelClient(
        api_key=api_key,
        api_base_url=settings.AI_API_BASE_URL,
        cascade_models=settings.ai_cascade_models_list,
        fallback_model=settings.AI_FALLBACK_MODEL,
        timeout=60.0, max_retries=2, backoff_base=2.0
    )

    system = build_system_prompt()
    user = """## Market Context
Symbol: BTC/USDT | Timeframe: 5m | Regime: trending
Price range: 60000 - 68000 | Last: 65000
Volatility: 1.85% | Trend: +8.33%

## Strategy: Trend Following EMA (BTC/USDT)
Template: trend_ema | Params: {'ema_fast': 10, 'ema_slow': 50}
PnL: +12.40% | Win rate: 62% | Sharpe: 1.32
Max drawdown: 8.20% | Trades: 47 | Score: 0.6824

## Task
Evaluate this strategy. Respond ONLY with JSON:
{"score": <0.0-1.0>, "verdict": "<PROMOTE|HOLD|DEMOTE>", "reasoning": "<explanation>", "confidence": <0.0-1.0>}"""

    response = await client.call_with_fallback(system, user)

    assert response.content, "Nessuna risposta dal modello"
    result = parse_eval_result(response.content, "test_strategy_id", response.model)

    assert 0.0 <= result.score <= 1.0, f"Score fuori range: {result.score}"
    assert result.verdict in ("PROMOTE", "HOLD", "DEMOTE"), f"Verdict invalido: {result.verdict}"
    assert len(result.reasoning) > 10, "Reasoning troppo corto"

    print(f"\n   ✅ REAL AI RESPONSE:")
    print(f"   Model: {response.model}")
    print(f"   Tokens used: {response.tokens_used}")
    print(f"   Score: {result.score}")
    print(f"   Verdict: {result.verdict}")
    print(f"   Confidence: {result.confidence}")
    print(f"   Reasoning: {result.reasoning[:300]}")
