import { Strategy } from './strategy.model';

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
  active_strategy: Partial<Strategy> | null;
  engine_status: string;
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
