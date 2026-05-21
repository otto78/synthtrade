from typing import List
from app.models.trade import Trade, TradeWithStrategy
from app.db.repositories.mode_filter import ModeFilterMixin


def _calc_pnl_eur(trade: dict) -> float | None:
    """Calculate net PnL in EUR for a closed trade."""
    price = trade.get("price")
    exit_price = trade.get("exit_price")
    quantity = trade.get("quantity")
    if price is None or quantity is None:
        return None
    if exit_price is None:
        return None
    action = trade.get("action", "BUY")
    diff = (exit_price - price) if action == "BUY" else (price - exit_price)
    return round(diff * quantity, 2)


class TradeRepository(ModeFilterMixin):
    def __init__(self, db):
        self.db = db
        self.table_name = "trades"

    def list_all(self, status: str | None = None, limit: int = 50) -> List[Trade]:
        query = self.db.table(self.table_name).select("*")
        query = self._apply_trading_mode_filter(query)
        if status:
            query = query.eq("status", status)
        res = query.order("executed_at", desc=True).limit(limit).execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def list_trades_with_strategies(
        self,
        status: str | None = None,
        action: str | None = None,
        strategy_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TradeWithStrategy]:
        """Lista trade con nome strategia via LEFT JOIN, con filtri opzionali."""
        query = self.db.table(self.table_name).select("*, strategies!left(title)")
        query = self._apply_trading_mode_filter(query)
        if status:
            query = query.eq("status", status)
        if action:
            query = query.eq("action", action.upper())
        if strategy_id:
            query = query.eq("strategy_id", strategy_id)
        res = query.order("executed_at", desc=True).limit(limit).offset(offset).execute()

        result: List[TradeWithStrategy] = []
        for t in res.data or []:
            strategies_rel = t.pop("strategies", None) or {}
            strategy_title = strategies_rel.get("title") if isinstance(strategies_rel, dict) else None
            # Enrich with computed pnl_eur if missing
            if t.get("pnl_eur") is None:
                t["pnl_eur"] = _calc_pnl_eur(t)
            result.append(TradeWithStrategy(
                **t,
                strategy_title=strategy_title,
            ))
        return result

    def get_distinct_strategy_ids(self) -> List[dict]:
        """Restituisce strategy_id + strategy_title distinti presenti nei trade."""
        query = self.db.table(self.table_name).select("strategy_id, strategies!left(title)")
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        seen: dict[str, str | None] = {}
        for t in res.data or []:
            sid = t.get("strategy_id")
            if not sid:
                continue
            strategies_rel = t.get("strategies") or {}
            title = strategies_rel.get("title") if isinstance(strategies_rel, dict) else None
            if sid not in seen:
                seen[sid] = title
        return [{"id": k, "title": v} for k, v in seen.items()]

    def list_active_with_strategies(self) -> List[dict]:
        query = self.db.table(self.table_name).select("*, strategies(*)").eq("status", "OPEN")
        query = self._apply_trading_mode_filter(query)
        res = query.order("executed_at", desc=True).execute()
        return res.data or []

    def get_since(self, since_iso: str) -> List[Trade]:
        query = self.db.table(self.table_name).select("*").gte("executed_at", since_iso)
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_history(self) -> List[dict]:
        query = self.db.table(self.table_name).select("executed_at,cost_eur,pnl_pct")
        query = self._apply_trading_mode_filter(query)
        res = query.order("executed_at").execute()
        return res.data or []

    def get_open_positions(self, symbol: str | None = None, strategy_id: str | None = None) -> List[Trade]:
        query = self.db.table(self.table_name).select("*").eq("status", "OPEN")
        query = self._apply_trading_mode_filter(query)
        if symbol:
            query = query.eq("pair", symbol)
        if strategy_id:
            query = query.eq("strategy_id", strategy_id)
        res = query.execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_closed_trades_by_strategy(self, strategy_id: str) -> List[Trade]:
        query = self.db.table(self.table_name).select("id, strategy_id, pair, action, price, quantity, pnl_pct, status, executed_at").eq("strategy_id", strategy_id).eq("status", "CLOSED")
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_open_by_strategy(self, strategy_id: str) -> List[Trade]:
        query = self.db.table(self.table_name).select("*").eq("strategy_id", strategy_id).eq("status", "OPEN")
        query = self._apply_trading_mode_filter(query)
        res = query.execute()
        return [Trade.model_validate(t) for t in res.data] if res.data else []

    def get_by_id(self, trade_id: str) -> Trade | None:
        query = self.db.table(self.table_name).select("*").eq("id", trade_id)
        query = self._apply_trading_mode_filter(query)
        res = query.single().execute()
        if res.data:
            return Trade.model_validate(res.data)
        return None

    def insert(self, trade_data: dict) -> Trade:
        trade_data = self._filter_for_write(trade_data)
        res = self.db.table(self.table_name).insert(trade_data).execute()
        return Trade.model_validate(res.data[0])

    def update(self, trade_id: str, update_data: dict):
        self.db.table(self.table_name).update(update_data).eq("id", trade_id).execute()