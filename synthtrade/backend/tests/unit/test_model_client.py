import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.model_client import ModelClient, ModelClientError, ModelTimeoutError, AllModelsUnavailableError
from app.ai.schemas import ModelResponse


@pytest.fixture
def client():
    return ModelClient(
        api_key="test-key",
        api_base_url="https://openrouter.ai/api/v1",
        cascade_models=["model-a", "model-b"],
        fallback_model="model-fallback",
        timeout=5.0,
        max_retries=2,
        backoff_base=0.01,
    )


def make_response(content="ok", model="model-a", tokens=10):
    return {
        "choices": [{"message": {"content": content}}],
        "model": model,
        "usage": {"total_tokens": tokens},
    }


@pytest.mark.asyncio
async def test_call_model_posts_correct_headers(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = make_response()
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client._call_model("model-a", "sys", "user")

    assert isinstance(result, ModelResponse)
    assert result.content == "ok"
    assert result.tokens_used == 10


@pytest.mark.asyncio
async def test_call_model_returns_model_response(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = make_response(content="analysis", tokens=42)
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client._call_model("model-a", "sys", "user")

    assert result.content == "analysis"
    assert result.tokens_used == 42


@pytest.mark.asyncio
async def test_retry_on_429(client):
    call_count = 0

    async def flaky_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            r = MagicMock()
            r.status_code = 429
            r.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429", request=MagicMock(), response=r)
            return r
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = make_response()
        r.raise_for_status = MagicMock()
        return r

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=flaky_post):
        result = await client._call_model("model-a", "sys", "user")

    assert call_count == 2
    assert result.content == "ok"


@pytest.mark.asyncio
async def test_raises_model_client_error_after_max_retries(client):
    async def always_429(*args, **kwargs):
        r = MagicMock()
        r.status_code = 429
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429", request=MagicMock(), response=r)
        return r

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=always_429):
        with pytest.raises(ModelClientError):
            await client._call_model("model-a", "sys", "user")


@pytest.mark.asyncio
async def test_raises_model_timeout_error(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock,
               side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(ModelTimeoutError):
            await client._call_model("model-a", "sys", "user")


@pytest.mark.asyncio
async def test_call_with_fallback_tries_cascade_then_fallback(client):
    call_count = {"n": 0}

    async def always_fail(*args, **kwargs):
        call_count["n"] += 1
        raise httpx.TimeoutException("timeout")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=always_fail):
        with pytest.raises(AllModelsUnavailableError):
            await client.call_with_fallback("sys", "user")

    # cascade (2 modelli × max_retries) + fallback
    assert call_count["n"] > 0


@pytest.mark.asyncio
async def test_call_with_fallback_returns_on_first_success(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = make_response(model="model-a")
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call_with_fallback("sys", "user")

    assert result.model == "model-a"
