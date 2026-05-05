import { Strategy } from './strategy.model';

export interface DashboardStats {
  balance: number;
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
