import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { errorInterceptor } from './error.interceptor';
import { AuthService } from '../services/auth.service';

describe('errorInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let authService: jest.Mocked<AuthService>;
  let router: jest.Mocked<Router>;

  beforeEach(() => {
    authService = { logout: jest.fn() } as any;
    router = { navigate: jest.fn() } as any;

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should call logout on 401', () => {
    http.get('/api/strategies').subscribe({ error: () => {} });

    const req = httpMock.expectOne('/api/strategies');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

    expect(authService.logout).toHaveBeenCalled();
  });

  it('should NOT call logout on 403', () => {
    http.get('/api/strategies').subscribe({ error: () => {} });

    const req = httpMock.expectOne('/api/strategies');
    req.flush('Forbidden', { status: 403, statusText: 'Forbidden' });

    expect(authService.logout).not.toHaveBeenCalled();
  });

  it('should propagate error on 500', (done) => {
    http.get('/api/strategies').subscribe({
      error: (err) => {
        expect(err.status).toBe(500);
        done();
      },
    });

    const req = httpMock.expectOne('/api/strategies');
    req.flush('Server Error', { status: 500, statusText: 'Internal Server Error' });
  });
});
