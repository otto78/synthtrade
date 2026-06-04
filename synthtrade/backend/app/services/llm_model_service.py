"""Service that provides LLM model configuration from the database.

Evaluators should use this service instead of reading from `settings`
directly, so that runtime changes to models (saved via the API) are
reflected immediately.
"""

from app.db.repositories.llm_model_repository import LLMModelRepository
from app.db.supabase_client import get_supabase
from app.config import settings
from app.ai.model_client import ModelClient
from typing import Optional


class LLMModelService:
    """Provides cascade and fallback model lists from the database.

    Usage::

        service = LLMModelService(repo)
        cascade, fallback = service.get_active_models()
    """

    def __init__(self, repo: Optional[LLMModelRepository] = None) -> None:
        """If no repo is given, create one from the default Supabase client."""
        if repo is None:
            repo = LLMModelRepository(get_supabase())
        self._repo = repo

    def get_active_models(self) -> tuple[list[str], str]:
        """Return (cascade_list, fallback) from the DB row.

        Falls back to settings-based defaults if no data exists or DB fails.
        """
        try:
            data = self._repo.get_models()
            cascade: list[str] = data.get("cascade", [])
            fallback: str = data.get("fallback", "")
            if cascade or fallback:
                return cascade, fallback
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to read models from DB, using settings fallback"
            )
        return settings.ai_cascade_models_list, settings.AI_FALLBACK_MODEL

    def create_model_client(self, **kwargs) -> ModelClient:
        """Create a ModelClient using models from the database.

        Any extra keyword arguments override the default ModelClient parameters.
        Always reads the latest cascade/fallback from DB at creation time,
        so changes made via the API are reflected immediately.
        """
        cascade, fallback = self.get_active_models()

        defaults = {
            "api_key": settings.OPENROUTER_API_KEY,
            "api_base_url": settings.AI_API_BASE_URL,
            "cascade_models": cascade,
            "fallback_model": fallback,
            "timeout": settings.AI_TIMEOUT_SECONDS,
            "max_retries": settings.AI_MAX_RETRIES,
            "backoff_base": settings.AI_BACKOFF_BASE,
        }
        # Merge defaults with any overrides provided by the caller
        defaults.update(kwargs)
        return ModelClient(**defaults)