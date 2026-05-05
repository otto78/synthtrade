export type TradeDirection = 'BUY' | 'SELL';
export type TradeStatus = 'OPEN' | 'CLOSED';

export interface Trade {
  id: string;
  strategy_id: string | null;
  action: TradeDirection;
  pair: string;
  price: number;
  quantity: number;
  cost_eur: number | null;
  fee_eur: number | null;
  pnl_pct: number | null;
  paper: boolean;
  executed_at: string;
}
