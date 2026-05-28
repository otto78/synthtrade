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

  constructor(private http: HttpClient) {}

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
  start(mode: 'paper' | 'live' = 'paper', strategy?: string, symbol?: string): Observable<ScalpingSession> {
    return this.controlSession({ action: 'start', mode, strategy, symbol });
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
}