export interface ScalpingSessionLog {
  id: string;
  symbol: string;
  mode: 'PAPER' | 'LIVE';
  status: 'running' | 'paused' | 'stopped';
  started_at: string;
  stopped_at?: string;
  duration_seconds?: number;
  total_pnl: number;
  total_pnl_pct?: number;
  trade_count: number;
  win_count: number;
  strategy?: string;
  trade_value?: number;
  // arricchito lato frontend dopo caricamento trade
  hold_pnl_pct?: number;
}

export interface SessionTradeLog {
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  exit_price?: number;
  quantity: number;
  pnl?: number;
  pnl_pct?: number;
  entry_time: string;
  exit_time?: string;
  signal_reason?: string;
  status?: string;
}
