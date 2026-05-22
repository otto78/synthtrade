import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { LLMModelsService } from '../services/llm-models.service';

/** Endpoints that use LLM models — errors here may indicate model failure. */
const MODEL_RELATED_PATTERNS = [
  /\/api\/strategies\/.*\/eval/,
  /\/api\/pipeline/,
  /\/api\/llm-models/,
];

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const llmModels = inject(LLMModelsService);
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401) {
        auth.logout();
      }
      // If any model-related endpoint fails (500/400/0), trigger a re-check
      const isModelRelated = MODEL_RELATED_PATTERNS.some(p => p.test(req.url));
      if (isModelRelated && err.status !== 401) {
        // Fire-and-forget: check model health in the background
        llmModels.checkModels().subscribe();
      }
      return throwError(() => err);
    })
  );
};
