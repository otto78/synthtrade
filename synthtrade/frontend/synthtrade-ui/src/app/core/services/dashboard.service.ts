import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay, timeout, catchError, of } from 'rxjs';
import { DashboardStats, BalanceSnapshot } from '../models/dashboard.model';
import { environment } from '../../../environments/environment';

const CACHE_TTL_MS = 30_000;
const REQUEST_TIMEOUT_MS = 15_000;

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/dashboard`;

  private stats$: Observable<DashboardStats> | null = null;
  private statsCreatedAt = 0;

  getStats(): Observable<DashboardStats> {
    const now = Date.now();
    if (!this.stats$ || now - this.statsCreatedAt > CACHE_TTL_MS) {
      this.statsCreatedAt = now;
      this.stats$ = this.http.get<DashboardStats>(this.base).pipe(
        timeout(REQUEST_TIMEOUT_MS),
        catchError(() => of({
          balance_eur: 0,
          balance_breakdown: {},
          balance_assets: [],
          pnl_today: 0,
          active_strategy: null,
          engine_status: 'OFFLINE',
        })),
        shareReplay(1)
      );
    }
    return this.stats$;
  }

  getEquityHistory(): Observable<BalanceSnapshot[]> {
    return this.http.get<BalanceSnapshot[]>(`${this.base}/equity-history`);
  }
}
