import asyncio
import json
import httpx
import logging
from app.ai.schemas import ModelResponse
from app.ai.retry import async_retry

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
        
        # Log obfuscated key to verify initialization
        key_show = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "***"
        logger.info(f"[ModelClient] Initialized with API Key: {key_show} and {len(cascade_models)} cascade models")

    @async_retry(max_retries=3, backoff_base=2.0, exceptions=(httpx.TimeoutException, httpx.HTTPStatusError, KeyError, IndexError, TypeError))
    async def _call_model(self, model: str, system: str, user: str) -> ModelResponse:
        if not self.api_key:
            logger.error(f"[ModelClient] API Key is empty! Cannot call {model}")
            raise ModelClientError("API Key is missing")

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

        async with httpx.AsyncClient(timeout=self.timeout) as http:
            resp = None
            try:
                resp = await http.post(f"{self.api_base_url}/chat/completions",
                                        headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                # Validate response structure — API may return error JSON with HTTP 200
                if "choices" not in data or not isinstance(data["choices"], list) or len(data["choices"]) == 0:
                    error_detail = data.get("error", {}).get("message", str(data))
                    logger.warning(f"[ModelClient] Malformed response from {model}: {error_detail}")
                    raise ModelClientError(f"Malformed response: no valid 'choices' in response")
                choice = data["choices"][0]
                if "message" not in choice or "content" not in choice["message"]:
                    raise ModelClientError(f"Malformed response: choice missing 'message.content'")
                return ModelResponse(
                    content=choice["message"]["content"],
                    model=data.get("model", model),
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )
            except (KeyError, IndexError, TypeError) as e:
                raise ModelClientError(f"Malformed response from {model}: {e}") from e
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code == 429:
                    logger.warning(f"[ModelClient] Rate limit (429) on {model}. Retry might trigger.")
                elif code == 401:
                    logger.error(f"[ModelClient] Authentication failed (401) on {model}. Check your OPENROUTER_API_KEY.")
                elif code >= 500:
                    logger.warning(f"[ModelClient] Server error ({code}) on {model}.")
                
                if code in (429, 503):
                    # Re-raise per trigger del decoratore
                    raise e
                raise ModelClientError(f"HTTP {code} on {model}") from e
            except json.JSONDecodeError as e:
                body_preview = resp.text[:500] if resp is not None else "N/A"
                logger.warning(f"[ModelClient] Invalid JSON from {model}: {e}. Body: {body_preview}")
                raise ModelClientError(f"Invalid JSON response from {model}") from e

    async def call_with_fallback(self, system: str, user: str) -> ModelResponse:
        all_models = self.cascade_models + [self.fallback_model]
        last_error: Exception | None = None

        for i, model in enumerate(all_models):
            is_fallback = (model == self.fallback_model)
            tier_label = "FALLBACK" if is_fallback else f"Tier {i+1}"
            
            try:
                if is_fallback and i > 0:
                    logger.warning(f"[ModelClient] Cascade exhausted. ACTIVATING FALLBACK: {model}")
                else:
                    logger.info(f"[ModelClient] Trying {tier_label}: {model}")

                result = await self._call_model(model, system, user)
                logger.info(f"[ModelClient] SUCCESS with {model}")
                return result
            except (ModelClientError, ModelTimeoutError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                logger.warning(f"[ModelClient] {tier_label} ({model}) FAILED: {e}")
                last_error = e
                continue

        logger.error("[ModelClient] CRITICAL: All models in cascade and fallback failed.")
        raise AllModelsUnavailableError("All models unavailable") from last_error
