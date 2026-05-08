import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Strategy, StrategyCreateDto, MonitorData } from '../models/strategy.model';
import { environment } from '../../../environments/environment';

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

  deleteStrategy(id: string): Observable<{ id: string; status: string }> {
    return this.http.delete<{ id: string; status: string }>(`${this.base}/${id}`);
  }

  getMonitorData(id: string): Observable<MonitorData> {
    return this.http.get<MonitorData>(`${environment.apiUrl}/monitor/${id}`);
  }
}
