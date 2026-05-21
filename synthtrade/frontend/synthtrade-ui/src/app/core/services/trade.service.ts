import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TradeWithStrategy, TradeStrategyInfo } from '../models/trade.model';
import { environment } from '../../../environments/environment';

export interface TradeFilters {
  status?: string;
  action?: string;
  strategy_id?: string;
  limit?: number;
  offset?: number;
}

@Injectable({ providedIn: 'root' })
export class TradeService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/trades`;

  getTrades(filters: TradeFilters = {}): Observable<TradeWithStrategy[]> {
    let params = new HttpParams();
    if (filters.status) params = params.set('status', filters.status);
    if (filters.action) params = params.set('action', filters.action);
    if (filters.strategy_id) params = params.set('strategy_id', filters.strategy_id);
    if (filters.limit != null) params = params.set('limit', filters.limit.toString());
    if (filters.offset != null) params = params.set('offset', filters.offset.toString());
    return this.http.get<TradeWithStrategy[]>(`${this.base}/list`, { params });
  }

  getStrategies(): Observable<TradeStrategyInfo[]> {
    return this.http.get<TradeStrategyInfo[]>(`${this.base}/strategies`);
  }
}