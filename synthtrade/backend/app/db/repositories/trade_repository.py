from typing import List, Optional
from app.models.trade import Trade

class TradeRepository:
    def __init__(self, db):
        self.db = db
        self.table_name = "trades"

    def list_all(self, status: Optional[str] = None, limit: int = 50) -> List[Trade]:
        query = self.db.table(self.table_name).select("*")
        if status:
            query = query.eq("status", status)
        res = query.order("executed_at", desc=True).limit(limit).execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def list_active_with_strategies(self) -> List[dict]:
        # Returns raw data because it's a join
        res = self.db.table(self.table_name).select("*, strategies(*)").eq("status", "OPEN").order("executed_at", desc=True).execute()
        return res.data or []

    def get_since(self, since_iso: str) -> List[Trade]:
        res = self.db.table(self.table_name).select("*").gte("executed_at", since_iso).execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_history(self) -> List[dict]:
        res = self.db.table(self.table_name).select("executed_at,cost_eur,pnl_pct").order("executed_at").execute()
        return res.data or []

    def get_open_positions(self, symbol: Optional[str] = None, strategy_id: Optional[str] = None) -> List[Trade]:
        query = self.db.table(self.table_name).select("*").eq("status", "OPEN")
        if symbol:
            query = query.eq("pair", symbol)
        if strategy_id:
            query = query.eq("strategy_id", strategy_id)
        res = query.execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_closed_trades_by_strategy(self, strategy_id: str) -> List[Trade]:
        res = self.db.table(self.table_name).select("price, quantity, pnl_pct").eq("strategy_id", strategy_id).eq("status", "CLOSED").execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_open_by_strategy(self, strategy_id: str) -> List[Trade]:
        res = self.db.table(self.table_name).select("*").eq("strategy_id", strategy_id).eq("status", "OPEN").execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_by_id(self, trade_id: str) -> Optional[Trade]:
        res = self.db.table(self.table_name).select("*").eq("id", trade_id).single().execute()
        if res.data:
            return Trade.model_validate(res.data)
        return None

    def insert(self, trade_data: dict) -> Trade:
        res = self.db.table(self.table_name).insert(trade_data).execute()
        return Trade.model_validate(res.data[0])

    def update(self, trade_id: str, update_data: dict):
        self.db.table(self.table_name).update(update_data).eq("id", trade_id).execute()
