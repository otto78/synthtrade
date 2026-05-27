/**
 * Performance API Service
 * REST client for performance metrics
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PerformanceMetrics {
  totalPnl: number;
  totalPnlPct: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  maxDrawdown: number;
  consecutiveLosses: number;
}

@Injectable({
  providedIn: 'root',
})
export class PerformanceApiService {
  private readonly API_URL = '/api/scalping/performance';

  constructor(private http: HttpClient) {}

  /** Get performance metrics */
  /** Backend raw response shape (snake_case) */
  private _getMetricsRaw(): Observable<Record<string, number>> {
    return this.http.get<Record<string, number>>(this.API_URL);
  }

  getMetrics(): Observable<PerformanceMetrics> {
    // Backend returns snake_case, interface uses camelCase — map it
    return new Observable<PerformanceMetrics>((subscriber) => {
      this._getMetricsRaw().subscribe({
        next: (raw) => {
          subscriber.next({
            totalPnl: raw['total_pnl'] ?? 0,
            totalPnlPct: raw['total_pnl_pct'] ?? 0,
            winRate: (raw['win_rate'] ?? 0) / 100,
            totalTrades: raw['total_trades'] ?? 0,
            winningTrades: raw['winning_trades'] ?? 0,
            losingTrades: raw['losing_trades'] ?? 0,
            avgWin: raw['avg_win'] ?? 0,
            avgLoss: raw['avg_loss'] ?? 0,
            profitFactor: raw['profit_factor'] ?? 0,
            maxDrawdown: raw['max_drawdown'] ?? 0,
            consecutiveLosses: raw['consecutive_losses'] ?? 0,
          });
          subscriber.complete();
        },
        error: (err) => subscriber.error(err),
      });
    });
  }
}