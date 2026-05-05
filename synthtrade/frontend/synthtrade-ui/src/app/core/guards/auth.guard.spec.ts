import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { authGuard } from './auth.guard';
import { TokenStorageService } from '../services/token-storage.service';
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';

describe('authGuard', () => {
  let tokenStorage: jest.Mocked<TokenStorageService>;
  let router: jest.Mocked<Router>;

  const route = {} as ActivatedRouteSnapshot;
  const state = { url: '/dashboard' } as RouterStateSnapshot;

  beforeEach(() => {
    tokenStorage = {
      getAccessToken: jest.fn(),
      isTokenExpired: jest.fn(),
      setTokens: jest.fn(),
      clear: jest.fn(),
    } as any;
    router = { navigate: jest.fn(), createUrlTree: jest.fn().mockReturnValue('/login') } as any;

    TestBed.configureTestingModule({
      providers: [
        { provide: TokenStorageService, useValue: tokenStorage },
        { provide: Router, useValue: router },
      ],
    });
  });

  const runGuard = () => TestBed.runInInjectionContext(() => authGuard(route, state));

  it('should allow access when token is valid', () => {
    tokenStorage.getAccessToken.mockReturnValue('valid-token');
    tokenStorage.isTokenExpired.mockReturnValue(false);

    const result = runGuard();
    expect(result).toBe(true);
  });

  it('should redirect to /login when token is absent', () => {
    tokenStorage.getAccessToken.mockReturnValue(null);

    const result = runGuard();
    expect(result).not.toBe(true);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
  });

  it('should redirect to /login when token is expired', () => {
    tokenStorage.getAccessToken.mockReturnValue('expired-token');
    tokenStorage.isTokenExpired.mockReturnValue(true);

    const result = runGuard();
    expect(result).not.toBe(true);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
  });
});
