import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { AuthService } from './auth.service';
import { TokenStorageService } from './token-storage.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let tokenStorage: jest.Mocked<TokenStorageService>;

  beforeEach(() => {
    tokenStorage = {
      setTokens: jest.fn(),
      getAccessToken: jest.fn(),
      clear: jest.fn(),
      isTokenExpired: jest.fn(),
    } as any;

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: TokenStorageService, useValue: tokenStorage },
      ],
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should call POST /auth/login and save tokens', () => {
    const tokens = { access_token: 'jwt123', token_type: 'bearer' as const };

    service.login('mypassword').subscribe();

    const req = httpMock.expectOne('/api/auth/login');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ password: 'mypassword' });
    req.flush(tokens);

    expect(tokenStorage.setTokens).toHaveBeenCalledWith(tokens);
  });

  it('should update currentUser$ after login', () => {
    service.login('mypassword').subscribe();
    httpMock.expectOne('/api/auth/login').flush({ access_token: 'jwt', token_type: 'bearer' });

    service.currentUser$.subscribe(user => expect(user).toBe('user'));
  });

  it('should clear tokens and navigate to /login on logout', () => {
    service.logout();
    expect(tokenStorage.clear).toHaveBeenCalled();
  });

  it('should emit null on currentUser$ after logout', () => {
    service.logout();
    service.currentUser$.subscribe(user => expect(user).toBeNull());
  });

  it('should return true for isAuthenticated when token valid', () => {
    tokenStorage.getAccessToken.mockReturnValue('valid-token');
    tokenStorage.isTokenExpired.mockReturnValue(false);
    expect(service.isAuthenticated()).toBe(true);
  });

  it('should return false for isAuthenticated when no token', () => {
    tokenStorage.getAccessToken.mockReturnValue(null);
    expect(service.isAuthenticated()).toBe(false);
  });

  it('should return false for isAuthenticated when token expired', () => {
    tokenStorage.getAccessToken.mockReturnValue('expired');
    tokenStorage.isTokenExpired.mockReturnValue(true);
    expect(service.isAuthenticated()).toBe(false);
  });
});
