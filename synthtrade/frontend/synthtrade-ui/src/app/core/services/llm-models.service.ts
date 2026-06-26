import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, timeout, catchError, of, Subject, tap } from 'rxjs';
import { LLMModelsPayload } from '../models/llm-models.model';
import { environment } from '../../../environments/environment';

const REQUEST_TIMEOUT_MS = 10_000;

export interface ModelCheckResult {
  model: string;
  status: 'online' | 'offline';
}

export interface ModelsCheckResponse {
  checks: ModelCheckResult[];
  summary: 'all_ok' | 'partial' | 'all_down';
}

@Injectable({ providedIn: 'root' })
export class LLMModelsService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/llm-models`;

  /** Emitted whenever a health check completes — Topbar listens to stay in sync. */
  checkCompleted = new Subject<ModelsCheckResponse>();

  getModels(useCase: string = 'pipeline_eval'): Observable<LLMModelsPayload> {
    let params = new HttpParams().set('use_case', useCase);
    return this.http.get<LLMModelsPayload>(this.base, { params }).pipe(
      timeout(REQUEST_TIMEOUT_MS),
      catchError(err => {
        console.error('Error fetching LLM models:', err);
        return of({ cascade: [], fallback: '' } as LLMModelsPayload);
      })
    );
  }

  setModels(payload: LLMModelsPayload, useCase: string = 'pipeline_eval'): Observable<LLMModelsPayload> {
    let params = new HttpParams().set('use_case', useCase);
    return this.http.post<LLMModelsPayload>(this.base, payload, { params }).pipe(
      timeout(REQUEST_TIMEOUT_MS),
      catchError(err => {
        console.error('Error saving LLM models:', err);
        throw err;
      })
    );
  }

  checkModels(models?: string[], includeFallback = false, useCase: string = 'pipeline_eval'): Observable<ModelsCheckResponse> {
    let params = new HttpParams().set('use_case', useCase);
    if (models && models.length > 0) {
      for (const m of models) {
        params = params.append('models', m);
      }
    }
    if (includeFallback) {
      params = params.set('include_fallback', 'true');
    }
    return this.http.get<ModelsCheckResponse>(`${this.base}/check`, { params }).pipe(
      timeout(30_000),
      tap(res => this.checkCompleted.next(res)),
      catchError(err => {
        console.error('Error checking LLM models:', err);
        const fallback: ModelsCheckResponse = { checks: [], summary: 'all_down' };
        this.checkCompleted.next(fallback);
        return of(fallback);
      })
    );
  }
}