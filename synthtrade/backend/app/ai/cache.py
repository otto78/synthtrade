from datetime import datetime, UTC, timedelta
from app.db.supabase_client import get_supabase
from app.ai.schemas import EvalResult


class EvalCache:
    def __init__(self, ttl_minutes: int = 60):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.db = get_supabase()

    def get_cached_eval(self, strategy_id: str) -> EvalResult | None:
        res = self.db.table("ai_eval_cache").select("*").eq(
            "strategy_id", strategy_id).execute()
        if not res.data:
            return None

        row = res.data[0]
        evaluated_at = datetime.fromisoformat(row["evaluated_at"])
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=UTC)

        if datetime.now(UTC) - evaluated_at > self.ttl:
            return None

        return EvalResult(
            strategy_id=row["strategy_id"],
            score=row["score"],
            verdict=row["verdict"],
            reasoning=row["reasoning"],
            confidence=row["confidence"],
            model_used=row["model_used"],
            tokens_used=row.get("tokens_used", 0),
            evaluated_at=evaluated_at,
        )

    def save_eval(self, result: EvalResult) -> None:
        self.db.table("ai_eval_cache").upsert({
            "strategy_id": result.strategy_id,
            "score": result.score,
            "verdict": result.verdict,
            "reasoning": result.reasoning,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "tokens_used": result.tokens_used,
            "evaluated_at": result.evaluated_at.isoformat(),
        }).execute()
