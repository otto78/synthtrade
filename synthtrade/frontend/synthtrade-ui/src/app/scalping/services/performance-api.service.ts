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
  /** PnL % we'd have had by holding since first trade entry */
  holdPnlPct: number | null;
  /** True if trading PnL% beats hold PnL% */
  tradingBeatsHold: boolean | null;
}

@Injectable({
  providedIn: 'root',
})
export class PerformanceApiService {
  private readonly API_URL = '/api/scalping/performance';

  constructor(private http: HttpClient) {}

  /** Backend raw response shape (snake_case) */
  private _getMetricsRaw(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(this.API_URL);
  }

  getMetrics(): Observable<PerformanceMetrics> {
    // Backend returns snake_case, interface uses camelCase — map it
    return new Observable<PerformanceMetrics>((subscriber) => {
      this._getMetricsRaw().subscribe({
        next: (raw) => {
          const holdRaw = raw['hold_pnl_pct'];
          const beatsRaw = raw['trading_beats_hold'];
          subscriber.next({
            totalPnl: (raw['total_pnl'] as number) ?? 0,
            totalPnlPct: (raw['total_pnl_pct'] as number) ?? 0,
            winRate: ((raw['win_rate'] as number) ?? 0) / 100,
            totalTrades: (raw['total_trades'] as number) ?? 0,
            winningTrades: (raw['winning_trades'] as number) ?? 0,
            losingTrades: (raw['losing_trades'] as number) ?? 0,
            avgWin: (raw['avg_win'] as number) ?? 0,
            avgLoss: (raw['avg_loss'] as number) ?? 0,
            profitFactor: (raw['profit_factor'] as number) ?? 0,
            maxDrawdown: (raw['max_drawdown'] as number) ?? 0,
            consecutiveLosses: (raw['consecutive_losses'] as number) ?? 0,
            holdPnlPct: holdRaw !== undefined && holdRaw !== null ? (holdRaw as number) : null,
            tradingBeatsHold: beatsRaw !== undefined && beatsRaw !== null ? Boolean(beatsRaw) : null,
          });
          subscriber.complete();
        },
        error: (err) => subscriber.error(err),
      });
    });
  }
}