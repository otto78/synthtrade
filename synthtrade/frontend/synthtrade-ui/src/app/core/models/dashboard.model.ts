export interface BalanceAsset {
  asset: string;
  quantity: number;
  value_eur: number;
}

export interface BalanceBreakdown {
  [wallet: string]: {
    value_eur: number;
    assets: BalanceAsset[];
  };
}

export interface DashboardStats {
  balance_eur: number;
  balance_breakdown: BalanceBreakdown;
  balance_assets: BalanceAsset[];
  pnl_today: number;
  engine_status: string;
  active_strategies_count?: number;
  open_trades_count?: number;
  closed_trades_count?: number;
  closed_trades_pnl?: number;
  total_active_pnl_pct?: number;
  exchange_provider?: string;
}

export interface BalanceSnapshot {
  ts: string;
  value: number;
}

export interface PipelineStatus {
  last_run: string | null;
  next_run: string | null;
  strategies_generated: number;
  status: 'RUNNING' | 'IDLE' | 'ERROR';
}