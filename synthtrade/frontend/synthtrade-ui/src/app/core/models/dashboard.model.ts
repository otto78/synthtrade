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
  currency: string;
  balance_breakdown: BalanceBreakdown;
  balance_assets: BalanceAsset[];
  engine_status: string;
  active_strategies_count?: number;
  open_trades_count?: number;
  active_session_count?: number;
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