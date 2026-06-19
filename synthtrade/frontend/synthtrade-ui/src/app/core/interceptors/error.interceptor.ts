import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { LLMModelsService } from '../services/llm-models.service';

/** Endpoints that use LLM models — errors here may indicate model failure.
 * 
 * FIX-2026-06-12: Exclude /llm-models/check from triggering a re-check.
 * The check endpoint is already called periodically by the topbar; triggering
 * another check on error creates a loop: check fails → re-check → fails → ...
 * The topbar already handles the error case by setting status to 'all_down'.
 */
const MODEL_RELATED_PATTERNS = [
  /\/api\/strategies\/.*\/eval/,
  /\/api\/pipeline/,
  /\/api\/llm-models\/(?!check)/,  // exclude /check, match other /llm-models/*
];

/**
 * Scalping polling endpoints: these are polled every few seconds and may
 * transiently return 401 if the JWT is being refreshed or the WS reconnects.
 * FIX-2026-06-18: Do NOT trigger logout on 401 from these — the session lives
 * independently on the backend and a transient 401 should not kick the user out.
 * The user should only be logged out on 401 from auth-critical endpoints.
 */
const SCALPING_POLLING_PATTERNS = [
  /\/api\/scalping\/session/,
  /\/api\/scalping\/performance/,
  /\/api\/scalping\/position/,
  /\/api\/scalping\/intelligence/,
  /\/api\/scalping\/opportunity/,
  /\/ws\/scalping/,
];

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const llmModels = inject(LLMModelsService);
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401) {
        // Don't logout on transient 401 from scalping polling — would disconnect
        // the user from an active trading session for no reason.
        const isScalpingPolling = SCALPING_POLLING_PATTERNS.some(p => p.test(req.url));
        if (!isScalpingPolling) {
          auth.logout();
        }
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
