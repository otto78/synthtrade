import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';
import { ScalpingSessionLog, SessionTradeLog } from './logs.model';

@Injectable({ providedIn: 'root' })
export class ScalpingSessionLogsService {
  private http = inject(HttpClient);
  private base = '/api/scalping';

  getSessions(limit = 50, offset = 0): Observable<ScalpingSessionLog[]> {
    return this.http.get<ScalpingSessionLog[]>(
      `${this.base}/sessions?limit=${limit}&offset=${offset}`
    ).pipe(catchError(e => { console.warn('getSessions error', e); return of([]); }));
  }

  getSessionTrades(sessionId: string): Observable<SessionTradeLog[]> {
    return this.http.get<SessionTradeLog[]>(
      `${this.base}/trade-history?session_id=${sessionId}`
    ).pipe(catchError(e => { console.warn('getSessionTrades error', e); return of([]); }));
  }
}
