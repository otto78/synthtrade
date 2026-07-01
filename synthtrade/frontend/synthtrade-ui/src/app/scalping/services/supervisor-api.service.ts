import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SupervisorDecision } from './scalping-ws.service';

@Injectable({
  providedIn: 'root',
})
export class SupervisorApiService {
  private readonly API_URL = '/api/scalping/supervisor';

  constructor(private http: HttpClient) {}

  /** Get supervisor decision history for a specific session */
  getHistory(sessionId: string, limit: number = 50): Observable<SupervisorDecision[]> {
    return this.http.get<SupervisorDecision[]>(
      `${this.API_URL}/history`,
      { params: { session_id: sessionId, limit: limit.toString() } }
    );
  }
}