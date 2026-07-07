import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ScalpingSession, SessionControl } from '../models/session.model';

@Injectable({
  providedIn: 'root',
})
export class SessionApiService {
  private readonly API_URL = '/api/scalping/session';
  private sessionSubject = new BehaviorSubject<ScalpingSession | null>(null);
  session$ = this.sessionSubject.asObservable();

  /** Preview symbol: updated when user selects a symbol (even before session start) */
  private previewSymbolSubject = new BehaviorSubject<string>('BTCEUR');
  previewSymbol$ = this.previewSymbolSubject.asObservable();

  constructor(private http: HttpClient) {}

  /** Set the preview symbol (fires live chart update immediately) */
  setPreviewSymbol(symbol: string): void {
    this.previewSymbolSubject.next(symbol);
  }

  /** Update session data manually (e.g. from WebSocket) */
  updateSession(session: ScalpingSession | null): void {
    this.sessionSubject.next(session);
  }

  /** Get the current active session snapshot (synchronous) */
  getActiveSession(): import('../models/session.model').ScalpingSession | null {
    return this.sessionSubject.getValue();
  }

  /** Get current session status */
  getStatus(): Observable<ScalpingSession> {
    return this.http.get<ScalpingSession>(this.API_URL).pipe(
      tap(session => this.sessionSubject.next(session))
    );
  }

  /** Start/Pause/Stop session */
  controlSession(control: SessionControl): Observable<ScalpingSession> {
    return this.http.post<ScalpingSession>(this.API_URL, control).pipe(
      tap(session => {
        if (control.action === 'stop') {
          this.sessionSubject.next(null);
        } else {
          this.sessionSubject.next(session);
        }
      })
    );
  }

  /** Start session with specific mode */
  start(mode: 'paper' | 'live' = 'paper', strategy?: string, symbol?: string, tradeValue?: number): Observable<ScalpingSession> {
    return this.controlSession({ action: 'start', mode, strategy, symbol, trade_value: tradeValue });
  }

  /** Stop session */
  stop(): Observable<ScalpingSession> {
    return this.controlSession({ action: 'stop' });
  }

  /** Pause session */
  pause(): Observable<ScalpingSession> {
    return this.controlSession({ action: 'pause' });
  }

  /** Resume session */
  resume(): Observable<ScalpingSession> {
    return this.controlSession({ action: 'resume' });
  }

  /** Update trade value on active session (takes effect from next trade) */
  updateTradeValue(tradeValue: number): Observable<{ trade_value: number; status: string }> {
    return this.http.patch<{ trade_value: number; status: string }>(
      `${this.API_URL}/trade-value`,
      { trade_value: tradeValue }
    );
  }

  /** Download session log file as .txt */
  downloadSessionLogs(sessionId: string, symbol?: string): void {
    const url = `/api/scalping/session/${sessionId}/logs`;
    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: (blob: Blob) => {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `session_${symbol || 'UNKNOWN'}_${sessionId}_logs.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
      },
      error: (err) => {
        console.error('Failed to download session logs:', err);
      }
    });
  }
}
