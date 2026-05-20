import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, shareReplay, timeout, catchError, of, retry, timer } from 'rxjs';
import { DashboardStats, BalanceSnapshot } from '../models/dashboard.model';
import { environment } from '../../../environments/environment';

const CACHE_TTL_MS = 30_000;
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 3;

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/dashboard`;

  private stats$: Observable<DashboardStats> | null = null;
  private statsCreatedAt = 0;

  invalidateCache(): void {
    this.stats$ = null;
    this.statsCreatedAt = 0;
  }

  getStats(): Observable<DashboardStats> {
    const now = Date.now();
    if (!this.stats$ || now - this.statsCreatedAt > CACHE_TTL_MS) {
      this.statsCreatedAt = now;
      this.stats$ = this.http.get<DashboardStats>(this.base).pipe(
        timeout(REQUEST_TIMEOUT_MS),
        retry({
          count: MAX_RETRIES,
          delay: (error, retryCount) => timer(Math.pow(2, retryCount - 1) * 1000)
        }),
        catchError((err) => {
          console.error('Dashboard stats error after retries:', err);
          return of({
            balance_eur: 0,
            balance_breakdown: {},
            balance_assets: [],
            pnl_today: 0,
            engine_status: 'OFFLINE',
            active_strategies_count: 0,
            open_trades_count: 0,
            total_active_pnl_pct: 0,
          } as DashboardStats);
        }),
        shareReplay(1)
      );
    }
    return this.stats$;
  }

  getEquityHistory(range: string = '1m'): Observable<BalanceSnapshot[]> {
    const params = new HttpParams().set('range', range);
    return this.http.get<BalanceSnapshot[]>(`${this.base}/equity-history`, { params });
  }
}