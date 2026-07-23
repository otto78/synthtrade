/**
 * Position Models for Scalping Dashboard
 */

export interface Position {
  symbol: string;
  side: 'BUY' | 'SELL';
  position_side?: 'LONG' | 'SHORT';
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl: number;
  pnl_pct: number;
  leverage: number;
  opened_at: string;
  entry_time?: string;
  stop_loss?: number;
  take_profit?: number;
  // New fields for exit targets
  stop_loss_price?: number;
  take_profit_price?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  // TASK-885: Net targets (fee-adjusted)
  stop_loss_pct_net?: number;
  take_profit_pct_net?: number;
  // Trade size in USDC/USDT
  trade_value_usd?: number;
  // Breakeven: round-trip fee percentage (entry taker + exit maker)
  breakeven_pct?: number;
}
