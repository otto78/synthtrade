/**
 * Backtest API Service
 * REST client for backtest operations
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface BacktestConfig {
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  leverage: number;
  fee_rate: number;
}

export interface BacktestResult {
  config: BacktestConfig & { result_id: string };
  metrics: {
    total_trades: number;
    total_pnl: number;
    win_rate: number;
    max_drawdown: number;
    sharpe_ratio: number;
  };
  trades: any[];
}

@Injectable({
  providedIn: 'root',
})
export class BacktestApiService {
  private readonly API_URL = '/api/scalping/backtest';

  constructor(private http: HttpClient) {}

  /** Run a backtest */
  runBacktest(config: BacktestConfig): Observable<BacktestResult> {
    return this.http.post<BacktestResult>(`${this.API_URL}/run`, config);
  }

  /** Get backtest result by ID */
  getResult(resultId: string): Observable<BacktestResult> {
    return this.http.get<BacktestResult>(`${this.API_URL}/${resultId}/result`);
  }

  /** List all backtests */
  listBacktests(): Observable<BacktestResult[]> {
    return this.http.get<BacktestResult[]>(`${this.API_URL}/list`);
  }
}