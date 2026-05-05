import asyncio
import httpx
import logging
from app.ai.schemas import ModelResponse

logger = logging.getLogger(__name__)


class ModelClientError(Exception):
    pass


class ModelTimeoutError(ModelClientError):
    pass


class AllModelsUnavailableError(ModelClientError):
    pass


class ModelClient:
    def __init__(self, api_key: str, api_base_url: str,
                 cascade_models: list[str], fallback_model: str,
                 timeout: float = 30.0, max_retries: int = 3,
                 backoff_base: float = 2.0):
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.cascade_models = cascade_models
        self.fallback_model = fallback_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    async def _call_model(self, model: str, system: str, user: str) -> ModelResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://synthtrade.app",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as http:
                    resp = await http.post(f"{self.api_base_url}/chat/completions",
                                           headers=headers, json=body)
                    resp.raise_for_status()
                    data = resp.json()
                    return ModelResponse(
                        content=data["choices"][0]["message"]["content"],
                        model=data.get("model", model),
                        tokens_used=data.get("usage", {}).get("total_tokens", 0),
                    )
            except httpx.TimeoutException as e:
                raise ModelTimeoutError(f"Timeout on {model}") from e
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503):
                    last_error = e
                    wait = self.backoff_base ** attempt
                    logger.warning(f"{model} rate limited, retry {attempt+1} in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise ModelClientError(f"HTTP {e.response.status_code} on {model}") from e
            except Exception as e:
                raise ModelClientError(str(e)) from e

        raise ModelClientError(f"Max retries exceeded for {model}") from last_error

    async def call_with_fallback(self, system: str, user: str) -> ModelResponse:
        all_models = self.cascade_models + [self.fallback_model]
        last_error: Exception | None = None

        for model in all_models:
            try:
                result = await self._call_model(model, system, user)
                logger.info(f"AI response from {model}")
                return result
            except (ModelClientError, ModelTimeoutError) as e:
                logger.warning(f"Model {model} failed: {e}")
                last_error = e
                continue

        raise AllModelsUnavailableError("All models unavailable") from last_error
