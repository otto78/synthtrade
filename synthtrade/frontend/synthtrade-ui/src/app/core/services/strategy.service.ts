import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Strategy, StrategyCreateDto } from '../models/strategy.model';
import { environment } from '../../../environments/environment';

export interface ActivePnlItem {
  id: string;
  title: string;
  avg_pnl_pct: number;
  total_pnl_pct: number;
  current_value_usdt: number;
  open_trades_count: number;
}

export interface ActivePnlResponse {
  active_strategies_pnl: ActivePnlItem[];
}

export interface MonitorStrategyInfo {
  strategy: {
    id: string;
    title: string;
    status: string;
    pair: string;
    timeframe: string;
  };
  stats: {
    total_pnl_pct: number;
    total_pnl_eur: number;
    win_rate: number;
    total_trades: number;
    active_trades: number;
    equity_curve: number[];
  };
  recent_trades: Array<{
    id: string;
    executed_at: string;
    pair?: string;
    symbol?: string;
    action?: string;
    side?: string;
    pnl_pct: number;
    price: number;
    quantity: number;
    status: string;
    trade_type: string;
    strategy_id: string;
  }>;
}

@Injectable({ providedIn: 'root' })
export class StrategyService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/strategies`;

  getStrategies(status?: string): Observable<Strategy[]> {
    const params = status ? new HttpParams().set('strategy_status', status) : new HttpParams();
    return this.http.get<Strategy[]>(this.base, { params });
  }

  getStrategy(id: string): Observable<Strategy> {
    return this.http.get<Strategy>(`${this.base}/${id}`);
  }

  createStrategy(strategy: StrategyCreateDto): Observable<Strategy> {
    return this.http.post<Strategy>(this.base, strategy);
  }

  approve(id: string): Observable<{ id: string; status: string }> {
    return this.http.post<{ id: string; status: string }>(`${this.base}/${id}/approve`, {});
  }

  reject(id: string): Observable<{ id: string; status: string }> {
    return this.http.post<{ id: string; status: string }>(`${this.base}/${id}/reject`, {});
  }

  activate(id: string): Observable<{ id: string; status: string }> {
    return this.http.post<{ id: string; status: string }>(`${this.base}/${id}/activate`, {});
  }

  stop(id: string): Observable<{ id: string; status: string; closed_trades: number }> {
    return this.http.post<{ id: string; status: string; closed_trades: number }>(`${this.base}/${id}/stop`, {});
  }

  deleteStrategy(id: string): Observable<{ id: string; status: string }> {
    return this.http.delete<{ id: string; status: string }>(`${this.base}/${id}`);
  }

  getActivePnl(): Observable<ActivePnlResponse> {
    return this.http.get<ActivePnlResponse>(`${this.base}/active/pnl`);
  }

  getMonitorData(id: string): Observable<MonitorStrategyInfo> {
    return this.http.get<MonitorStrategyInfo>(`${environment.apiUrl}/monitor/${id}`);
  }
}