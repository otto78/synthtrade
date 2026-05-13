import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, timer } from 'rxjs';
import { exhaustMap, takeWhile, timeout } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { StrategyRequest, GenerationStatus } from '../models/strategy.model';

/** Timeout singola richiesta GET stato (evita hang silenziosi). */
const STATUS_POLL_REQUEST_MS = 60_000;

@Injectable({ providedIn: 'root' })
export class PipelineService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/pipeline`;

  /**
   * TASK-153: Avvia la generazione di strategie
   */
  generateStrategies(req: StrategyRequest): Observable<{ generation_id: string; status: string }> {
    return this.http.post<{ generation_id: string; status: string }>(`${this.base}/generate`, req);
  }

  /**
   * HALU-FE-02: Polling stato — primo tick immediato, una richiesta alla volta (no cancel da switchMap).
   */
  pollGenerationStatus(generationId: string): Observable<GenerationStatus> {
    return timer(0, 3000).pipe(
      exhaustMap(() =>
        this.http
          .get<GenerationStatus>(`${this.base}/generate/${generationId}/status`)
          .pipe(timeout(STATUS_POLL_REQUEST_MS))
      ),
      takeWhile(
        (status) => status.status === 'pending' || status.status === 'running',
        true
      )
    );
  }
}
