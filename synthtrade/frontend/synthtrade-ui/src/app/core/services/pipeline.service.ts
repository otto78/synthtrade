import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, switchMap, takeWhile } from 'rxjs';
import { environment } from '../../../environments/environment';
import { StrategyRequest, GenerationStatus } from '../models/strategy.model';

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
   * TASK-154: Polling dello stato della generazione
   */
  pollGenerationStatus(generationId: string): Observable<GenerationStatus> {
    return interval(3000).pipe(
      switchMap(() => this.http.get<GenerationStatus>(`${this.base}/generate/${generationId}/status`)),
      takeWhile(
        (status) => status.status === 'pending' || status.status === 'running',
        true // include the final status that breaks the condition
      )
    );
  }
}
