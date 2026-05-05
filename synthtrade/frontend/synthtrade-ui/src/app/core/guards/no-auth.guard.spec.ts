import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { noAuthGuard } from './no-auth.guard';
import { TokenStorageService } from '../services/token-storage.service';
import { ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';

describe('noAuthGuard', () => {
  let tokenStorage: jest.Mocked<TokenStorageService>;
  let router: jest.Mocked<Router>;

  const route = {} as ActivatedRouteSnapshot;
  const state = { url: '/login' } as RouterStateSnapshot;

  beforeEach(() => {
    tokenStorage = {
      getAccessToken: jest.fn(),
      isTokenExpired: jest.fn(),
      setTokens: jest.fn(),
      clear: jest.fn(),
    } as any;
    router = { navigate: jest.fn(), createUrlTree: jest.fn().mockReturnValue('/dashboard') } as any;

    TestBed.configureTestingModule({
      providers: [
        { provide: TokenStorageService, useValue: tokenStorage },
        { provide: Router, useValue: router },
      ],
    });
  });

  const runGuard = () => TestBed.runInInjectionContext(() => noAuthGuard(route, state));

  it('should allow access when user is NOT authenticated', () => {
    tokenStorage.getAccessToken.mockReturnValue(null);

    const result = runGuard();
    expect(result).toBe(true);
  });

  it('should redirect to /dashboard when user IS authenticated', () => {
    tokenStorage.getAccessToken.mockReturnValue('valid-token');
    tokenStorage.isTokenExpired.mockReturnValue(false);

    const result = runGuard();
    expect(result).not.toBe(true);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
  });
});
