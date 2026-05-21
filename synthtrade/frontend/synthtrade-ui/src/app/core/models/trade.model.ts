export interface TradeWithStrategy {
  id: string;
  strategy_id: string;
  strategy_title: string | null;
  pair: string;
  action: 'BUY' | 'SELL';
  status: 'OPEN' | 'CLOSED';
  price: number;
  quantity: number;
  pnl_pct: number | null;
  pnl_eur: number | null;
  exit_price: number | null;
  executed_at: string | null;
  closed_at: string | null;
  created_at: string | null;
}

export interface TradeStrategyInfo {
  id: string;
  title: string | null;
}