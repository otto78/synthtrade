/**
 * Session API Service
 * REST client for scalping session management
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ScalpingSession, SessionControl } from '../models/session.model';

@Injectable({
  providedIn: 'root',
})
export class SessionApiService {
  private readonly API_URL = '/api/scalping/session';

  constructor(private http: HttpClient) {}

  /** Get current session status */
  getStatus(): Observable<ScalpingSession> {
    return this.http.get<ScalpingSession>(this.API_URL);
  }

  /** Start/Pause/Stop session */
  controlSession(control: SessionControl): Observable<ScalpingSession> {
    return this.http.post<ScalpingSession>(this.API_URL, control);
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