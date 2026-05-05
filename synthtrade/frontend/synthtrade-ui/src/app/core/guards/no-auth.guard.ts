import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { TokenStorageService } from '../services/token-storage.service';

export const noAuthGuard: CanActivateFn = () => {
  const tokenStorage = inject(TokenStorageService);
  const router = inject(Router);

  const token = tokenStorage.getAccessToken();
  if (!token || tokenStorage.isTokenExpired()) {
    return true;
  }
  return router.createUrlTree(['/dashboard']);
};
