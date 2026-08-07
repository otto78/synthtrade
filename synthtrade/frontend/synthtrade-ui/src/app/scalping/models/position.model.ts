/**
 * Position Models for Scalping Dashboard
 */

// TASK-1249: step di trailing ancora da raggiungere (per barrette sulla progress bar)
export interface TrailingStep {
  step: number;
  trigger_net_pct: number;
  trigger_price: number;
}

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
  // TASK-1243: profit lock (break-even amend attivato)
  profit_lock_active?: boolean;
  profit_lock_sl_price?: number;
  // TASK-1246: trailing stop step (solo UI/telemetria)
  trailing_step?: number;
  // TASK-1247: rendimento netto % effettivo al prezzo SL corrente (post amend)
  sl_net_pct?: number;
  // TASK-1249: step di trailing rimanenti (per le barrette UI)
  trailing_steps?: TrailingStep[];
}
