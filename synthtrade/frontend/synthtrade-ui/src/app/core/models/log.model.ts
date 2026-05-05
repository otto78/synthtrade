export type LogLevel = 'BUY' | 'SELL' | 'SKIP' | 'BLOCK' | 'ERROR';

export interface OperationLog {
  id: string;
  strategy_id: string | null;
  action: LogLevel;
  price: number | null;
  quantity: number | null;
  reason: string | null;
  ai_score: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface LogFilters {
  action?: LogLevel;
  strategy_id?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedLogs {
  data: OperationLog[];
  total: number;
  limit: number;
  offset: number;
}
