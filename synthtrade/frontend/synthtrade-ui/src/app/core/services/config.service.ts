import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay, timeout, catchError, of } from 'rxjs';
import { ModeInfo } from '../models/config.model';
import { environment } from '../../../environments/environment';

const REQUEST_TIMEOUT_MS = 10_000;

@Injectable({ providedIn: 'root' })
export class ConfigService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/config`;

  private mode$: Observable<ModeInfo> | null = null;

  getMode(): Observable<ModeInfo> {
    if (!this.mode$) {
      this.mode$ = this.http.get<ModeInfo>(`${this.base}/mode`).pipe(
        timeout(REQUEST_TIMEOUT_MS),
        catchError((err) => {
          console.error('Config mode fetch error:', err);
          return of({
            mode: 'test',
            allow_live: false,
            details: 'Error fetching mode — defaulting to TEST',
          } as ModeInfo);
        }),
        shareReplay(1)
      );
    }
    return this.mode$;
  }

  setMode(mode: 'test' | 'live'): Observable<ModeInfo> {
    this.mode$ = null; // Invalida cache
    return this.http.post<ModeInfo>(`${this.base}/mode`, { mode }).pipe(
      timeout(REQUEST_TIMEOUT_MS),
      catchError((err) => {
        console.error('Config mode switch error:', err);
        throw err;
      })
    );
  }

  invalidateCache(): void {
    this.mode$ = null;
  }
}