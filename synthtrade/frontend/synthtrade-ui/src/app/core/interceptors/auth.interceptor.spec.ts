import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { authInterceptor } from './auth.interceptor';
import { TokenStorageService } from '../services/token-storage.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let tokenStorage: jest.Mocked<TokenStorageService>;

  beforeEach(() => {
    tokenStorage = { getAccessToken: jest.fn(), setTokens: jest.fn(), clear: jest.fn(), isTokenExpired: jest.fn() } as any;

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: TokenStorageService, useValue: tokenStorage },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should add Authorization header when token is present', () => {
    tokenStorage.getAccessToken.mockReturnValue('test-token');

    http.get('/api/strategies').subscribe();

    const req = httpMock.expectOne('/api/strategies');
    expect(req.request.headers.get('Authorization')).toBe('Bearer test-token');
    req.flush([]);
  });

  it('should NOT add Authorization header when token is absent', () => {
    tokenStorage.getAccessToken.mockReturnValue(null);

    http.get('/api/strategies').subscribe();

    const req = httpMock.expectOne('/api/strategies');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush([]);
  });
});
