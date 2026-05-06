export type StrategyStatus = 'PENDING' | 'APPROVED' | 'ACTIVE' | 'REJECTED' | 'EXPIRED';

export interface StrategyMetrics {
  pnl_pct: number;
  win_rate: number;
  sharpe: number;
  max_drawdown_pct: number;
  num_trades: number;
}

export interface Strategy {
  id: string;
  title: string;
  description?: string;
  template: string;
  pair: string;
  timeframe: string;
  params: Record<string, number>;
  score: number | null;
  ai_score: number | null;
  ai_risk: 'LOW' | 'MEDIUM' | 'HIGH' | null;
  ai_note: string | null;
  ai_strengths: string[];
  ai_warnings: string[];
  status: StrategyStatus;
  backtest: StrategyMetrics | null;
  equity_curve: number[];
  created_at: string;
  updated_at: string;
}

export interface StrategyCreateDto {
  template: string;
  pair: string;
  timeframe: string;
  params: Record<string, number>;
}

export type RiskLevel = 'low' | 'medium' | 'high';
export type AssetClass = 'crypto' | 'stocks' | 'forex';

export interface StrategyRequest {
  budget_eur: number;
  duration_days: number;
  asset_class: AssetClass;
  risk_level: RiskLevel;
  symbols?: string[];
  free_text?: string;
  max_strategies?: number;
}

export type GenerationProgressStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface GenerationStatus {
  generation_id: string;
  status: GenerationProgressStatus;
  results?: Strategy[];
  error?: string;
}
