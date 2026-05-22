from app.db.supabase_client import get_supabase

class LLMModelRepository:
    """Repository to manage LLM model configuration stored in Supabase.

    The table ``llm_models`` is expected to have the following columns:
    - ``id`` (uuid primary key)
    - ``model_type`` (text) – either ``cascade`` or ``fallback``
    - ``order_index`` (int, nullable) – position in the cascade list
    - ``model_name`` (text) – the OpenRouter model identifier
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    def get_models(self):
        """Return a dict with ``cascade`` list and ``fallback`` string.

        If the table is empty, returns empty list and empty string.
        """
        # Fetch cascade models ordered by ``order_index``
        cascade_res = (
            self.db.table("llm_models")
            .select("model_name")
            .eq("model_type", "cascade")
            .order("order_index")
            .execute()
        )
        cascade = [row["model_name"] for row in cascade_res.data] if cascade_res.data else []

        # Fetch fallback model (should be a single row)
        fallback_res = (
            self.db.table("llm_models")
            .select("model_name")
            .eq("model_type", "fallback")
            .limit(1)
            .execute()
        )
        fallback = fallback_res.data[0]["model_name"] if fallback_res.data and len(fallback_res.data) > 0 else ""
        return {"cascade": cascade, "fallback": fallback}

    def set_models(self, cascade: list[str], fallback: str):
        """Replace the stored models with the provided values.

        All existing rows are removed and the new ones are inserted.
        """
        # Delete existing rows — add a WHERE clause that matches all rows
        # (Supabase requires explicit filter for safety)
        self.db.table("llm_models").delete().neq("model_type", "___nonexistent___").execute()

        # Insert cascade models with order_index
        for idx, name in enumerate(cascade):
            self.db.table("llm_models").insert({
                "model_type": "cascade",
                "order_index": idx,
                "model_name": name,
            }).execute()

        # Insert fallback model
        if fallback:
            self.db.table("llm_models").insert({
                "model_type": "fallback",
                "order_index": None,
                "model_name": fallback,
            }).execute()
