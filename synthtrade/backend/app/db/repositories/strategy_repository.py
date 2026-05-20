from typing import List, Optional
from app.models.strategy import Strategy
from app.db.repositories.mode_filter import ModeFilterMixin


class StrategyRepository(ModeFilterMixin):
    def __init__(self, db):
        self.db = db
        self.table_name = "strategies"

    def get_by_id(self, strategy_id: str) -> Optional[Strategy]:
        query = self.db.table(self.table_name).select("*").eq("id", strategy_id)
        query = self._apply_trading_mode_filter(query)
        res = query.single().execute()
        if res.data:
            return Strategy.model_validate(res.data)
        return None

    def get_active(self) -> List[Strategy]:
        return self.list_by_status("ACTIVE")

    def update_status(self, strategy_id: str, status: str):
        self.db.table(self.table_name).update({"status": status}).eq("id", strategy_id).execute()

    def delete(self, strategy_id: str):
        self.db.table(self.table_name).delete().eq("id", strategy_id).execute()

    def get_one_active(self) -> Optional[Strategy]:
        query = self.db.table(self.table_name).select("*").eq("status", "ACTIVE").limit(1)
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        return Strategy.model_validate(res.data[0]) if res.data else None

    def list_by_status(self, status: str) -> List[Strategy]:
        query = self.db.table(self.table_name).select("*").eq("status", status)
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        return [Strategy.model_validate(s) for s in res.data] if res.data else []

    def list_all(self, status: Optional[str] = None) -> List[Strategy]:
        query = self.db.table(self.table_name).select("*")
        if status:
            query = query.eq("status", status)
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        return [Strategy.model_validate(s) for s in res.data] if res.data else []

    def transition_expired_active(self, now_iso: str):
        query = self.db.table(self.table_name).update({"status": "EXPIRED"}).eq("status", "ACTIVE")
        if hasattr(query, "lt"):
            query = query.lt("expires_at", now_iso)
        query.execute()

    def cleanup_expired_pending(self, now_iso: str):
        self.db.table(self.table_name).delete().eq("status", "PENDING").lt("expires_at", now_iso).execute()

    def update(self, strategy_id: str, data: dict):
        self.db.table(self.table_name).update(data).eq("id", strategy_id).execute()

    def create(self, data: dict) -> Strategy:
        data = self._filter_for_write(data)
        res = self.db.table(self.table_name).insert(data).execute()
        return Strategy.model_validate(res.data[0])