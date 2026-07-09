/**
 * Session Models for Scalping Dashboard
 */

export interface ScalpingSession {
  session_id: string;
  /** UUID del DB (scalping_sessions.id) — usato per download logs, etc. */
  db_session_id?: string;
  status: 'idle' | 'running' | 'paused' | 'stopped';
  mode: 'paper' | 'live' | 'test';
  strategy: string;
  symbol: string;
  started_at?: string;
  stopped_at?: string;
  paper_balance: number;
  live_balance?: number;
  trade_value?: number;
  first_trade_entry?: number;
  hold_pnl_pct?: number;
  error_code?: string;
  error_message?: string;
}

export interface SessionControl {
  action: 'start' | 'stop' | 'pause' | 'resume';
  mode?: 'paper' | 'live' | 'test';
  strategy?: string;
  symbol?: string;
  trade_value?: number;
}