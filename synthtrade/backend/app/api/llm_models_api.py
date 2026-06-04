"""API endpoints for managing LLM model configuration stored in Supabase.

Provides:
- GET /llm-models        -> returns { cascade: string[], fallback: string }
- GET /llm-models/check  -> returns health-check status for each model
- POST /llm-models       -> accepts same shape, validates, stores via LLMModelRepository
"""

import asyncio
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from app.dependencies import get_current_user
from app.db.repositories.llm_model_repository import LLMModelRepository
from app.db.supabase_client import get_supabase
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-models", tags=["llm-models"])

PING_TIMEOUT = 10.0


def get_repo(supabase = Depends(get_supabase)) -> LLMModelRepository:
    return LLMModelRepository(supabase)


class LLMModelsPayload(BaseModel):
    """Payload for the POST request — requires non‑empty fallback."""
    cascade: list[str] = Field(..., description="Ordered list of cascade model identifiers")
    fallback: str = Field(..., description="Fallback model identifier")

    @validator('cascade')
    def cascade_non_empty(cls, v):
        if not isinstance(v, list) or any(not isinstance(i, str) or not i for i in v):
            raise ValueError('cascade must be a list of non‑empty strings')
        return v

    @validator('fallback')
    def fallback_non_empty(cls, v):
        if not isinstance(v, str) or not v:
            raise ValueError('fallback must be a non‑empty string')
        return v


class LLMModelsResponse(BaseModel):
    """Response model for GET — allows empty fallback when no data exists."""
    cascade: list[str] = Field(default_factory=list, description="Ordered list of cascade model identifiers")
    fallback: str = Field(default="", description="Fallback model identifier")


class ModelCheckResult(BaseModel):
    """Result of a single model health-check."""
    model: str
    status: str  # "online" | "offline"


class ModelsCheckResponse(BaseModel):
    """Response for the health-check endpoint."""
    checks: list[ModelCheckResult]
    summary: str  # "all_ok" | "partial" | "all_down"


async def _ping_model(model: str, api_key: str, api_base: str) -> ModelCheckResult:
    """Send a minimal chat completion to check if a model responds."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://synthtrade.app",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "ok"}],
        "max_tokens": 5,
    }
    try:
        async with httpx.AsyncClient(timeout=PING_TIMEOUT) as http:
            resp = await http.post(f"{api_base}/chat/completions", headers=headers, json=body)
            if resp.status_code == 200:
                return ModelCheckResult(model=model, status="online")
            else:
                logger.warning("Model %s responded HTTP %d", model, resp.status_code)
                return ModelCheckResult(model=model, status="offline")
    except (httpx.TimeoutException, httpx.HTTPError, Exception) as e:
        logger.warning("Model %s ping failed: %s", model, e)
        return ModelCheckResult(model=model, status="offline")


@router.get("", response_model=LLMModelsResponse)
def get_models(repo: LLMModelRepository = Depends(get_repo), _user: str = Depends(get_current_user)):
    data = repo.get_models()
    return {"cascade": data.get('cascade', []), "fallback": data.get('fallback', '')}


@router.get("/check", response_model=ModelsCheckResponse)
async def check_models(
    repo: LLMModelRepository = Depends(get_repo),
    _user: str = Depends(get_current_user),
    models: list[str] | None = Query(default=None),
    include_fallback: bool = False,
):
    """Ping configured models and return their status.

    By default only **cascade** models are pinged (free tier). The
    ``include_fallback`` param controls whether the pay-per-use fallback
    model is also checked.

    If ``models`` query param is provided (repeatable), only those models
    are pinged instead of the DB contents. This is used by the frontend
    to validate proposed changes before saving.

    Responses are returned asynchronously — the frontend should update
    indicators once the response arrives.
    """
    if models:
        # Use provided models (e.g. from form before saving)
        all_models = list(dict.fromkeys(models))  # dedup preserving order
    else:
        data = repo.get_models()
        cascade: list[str] = data.get('cascade', [])
        fallback: str = data.get('fallback', '')
        all_models: list[str] = list(cascade)
        if include_fallback and fallback and fallback not in all_models:
            all_models.append(fallback)

    if not all_models:
        return ModelsCheckResponse(checks=[], summary="all_down")

    api_key = settings.OPENROUTER_API_KEY
    api_base = settings.AI_API_BASE_URL

    # Ping all models in parallel
    results = await asyncio.gather(*[
        _ping_model(model, api_key, api_base) for model in all_models
    ])

    online = sum(1 for r in results if r.status == "online")
    total = len(results)

    if online == total:
        summary = "all_ok"
    elif online == 0:
        summary = "all_down"
    else:
        summary = "partial"

    return ModelsCheckResponse(checks=results, summary=summary)


@router.post("", response_model=LLMModelsPayload, status_code=status.HTTP_200_OK)
def set_models(payload: LLMModelsPayload, repo: LLMModelRepository = Depends(get_repo), _user: str = Depends(get_current_user)):
    try:
        repo.set_models(payload.cascade, payload.fallback)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return payload