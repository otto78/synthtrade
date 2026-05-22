"""Service that provides LLM model configuration from the database.

Evaluators should use this service instead of reading from `settings`
directly, so that runtime changes to models (saved via the API) are
reflected immediately.
"""

from app.db.repositories.llm_model_repository import LLMModelRepository


class LLMModelService:
    """Provides cascade and fallback model lists from the database.

    Usage::

        service = LLMModelService(repo)
        cascade, fallback = service.get_active_models()
    """

    def __init__(self, repo: LLMModelRepository) -> None:
        self._repo = repo

    def get_active_models(self) -> tuple[list[str], str]:
        """Return (cascade_list, fallback) from the DB row.

        Falls back to an empty list and empty string if no data exists.
        """
        data = self._repo.get_models()
        cascade: list[str] = data.get("cascade", [])
        fallback: str = data.get("fallback", "")
        return cascade, fallback