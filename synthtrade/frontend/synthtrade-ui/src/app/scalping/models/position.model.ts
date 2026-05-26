/**
 * Position Models for Scalping Dashboard
 */

export interface Position {
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl: number;
  pnl_pct: number;
  leverage: number;
  opened_at: string;
  stop_loss?: number;
  take_profit?: number;
}