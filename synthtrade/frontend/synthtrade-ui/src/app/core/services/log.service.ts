import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { OperationLog, LogFilters } from '../models/log.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class LogService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/logs`;

  getLogs(filters: LogFilters): Observable<OperationLog[]> {
    let params = new HttpParams();
    if (filters.action) params = params.set('action', filters.action);
    if (filters.strategy_id) params = params.set('strategy_id', filters.strategy_id);
    if (filters.limit != null) params = params.set('limit', filters.limit.toString());
    if (filters.offset != null) params = params.set('offset', filters.offset.toString());
    return this.http.get<OperationLog[]>(this.base, { params });
  }

  exportCsv(): Observable<string> {
    return this.http.get(`${this.base}/export`, { responseType: 'text' });
  }
}
