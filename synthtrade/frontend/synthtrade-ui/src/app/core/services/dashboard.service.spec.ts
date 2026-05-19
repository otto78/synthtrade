import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { DashboardService } from './dashboard.service';

const MOCK_STATS = { balance: 1000, pnl_today: 50, active_strategy: null, engine_status: 'RUNNING' };
const MOCK_EQUITY = [{ ts: '2024-01-01T00:00:00', value: 1000 }];

describe('DashboardService', () => {
  let service: DashboardService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [DashboardService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(DashboardService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should call GET /dashboard', () => {
    service.getStats().subscribe();
    const req = httpMock.expectOne('/api/dashboard');
    expect(req.request.method).toBe('GET');
    req.flush(MOCK_STATS);
  });

  it('should call GET /dashboard/equity-history', () => {
    service.getEquityHistory().subscribe();
    const req = httpMock.expectOne('/api/dashboard/equity-history');
    expect(req.request.method).toBe('GET');
    req.flush(MOCK_EQUITY);
  });

  it('should cache getStats and not repeat HTTP call within 30s', fakeAsync(() => {
    let callCount = 0;

    service.getStats().subscribe(() => callCount++);
    httpMock.expectOne('/api/dashboard').flush(MOCK_STATS);

    service.getStats().subscribe(() => callCount++);
    httpMock.expectNone('/api/dashboard');

    expect(callCount).toBe(2);
    tick(31000);
  }));

  it('should repeat HTTP call after 30s cache expiry', fakeAsync(() => {
    service.getStats().subscribe();
    httpMock.expectOne('/api/dashboard').flush(MOCK_STATS);

    tick(31000);

    service.getStats().subscribe();
    httpMock.expectOne('/api/dashboard').flush(MOCK_STATS);
  }));

  // TASK-187: Test gestione errori e timeout
  it('should handle timeout error gracefully', fakeAsync(() => {
    let data: any = null;

    service.getStats().subscribe({
      next: (val) => data = val,
    });

    // Con retry attivo, ci saranno 4 richieste (1 iniziale + 3 retry)
    for (let i = 0; i < 4; i++) {
      const req = httpMock.expectOne('/api/dashboard');
      req.error(new ProgressEvent('timeout'));
      if (i < 3) tick(Math.pow(2, i) * 1000); // Exponential backoff
    }

    // Dopo tutti i retry falliti, ritorna fallback
    expect(data).toBeTruthy();
    expect(data.engine_status).toBe('OFFLINE');
  }));

  it('should handle network error with fallback', fakeAsync(() => {
    let data: any = null;

    service.getStats().subscribe({
      next: (val) => data = val,
    });

    // Con retry attivo, gestisce 4 tentativi
    for (let i = 0; i < 4; i++) {
      const req = httpMock.expectOne('/api/dashboard');
      req.error(new ProgressEvent('Network error'));
      if (i < 3) tick(Math.pow(2, i) * 1000);
    }

    expect(data).toBeTruthy();
    expect(data.balance_eur).toBe(0);
    expect(data.engine_status).toBe('OFFLINE');
  }));

  it('should retry on failure with exponential backoff', fakeAsync(() => {
    let attemptCount = 0;

    service.getStats().subscribe();

    // Prima chiamata fallisce
    attemptCount++;
    const req1 = httpMock.expectOne('/api/dashboard');
    req1.error(new ProgressEvent('Error'));

    // Deve fare retry dopo 1s
    tick(1000);
    attemptCount++;
    const req2 = httpMock.expectOne('/api/dashboard');
    req2.error(new ProgressEvent('Error'));

    // Deve fare retry dopo 2s
    tick(2000);
    attemptCount++;
    const req3 = httpMock.expectOne('/api/dashboard');
    req3.flush(MOCK_STATS);

    expect(attemptCount).toBe(3);
  }));

  it('should invalidate cache and fetch fresh data when forced', fakeAsync(() => {
    // Prima chiamata con cache
    service.getStats().subscribe();
    httpMock.expectOne('/api/dashboard').flush(MOCK_STATS);

    // Seconda chiamata riusa cache
    service.getStats().subscribe();
    httpMock.expectNone('/api/dashboard');

    // Force refresh invalida cache
    service.invalidateCache();
    service.getStats().subscribe();
    httpMock.expectOne('/api/dashboard').flush(MOCK_STATS);
  }));

  it('should not propagate sensitive error details to UI', fakeAsync(() => {
    let receivedError: any = null;
    let receivedData: any = null;

    service.getStats().subscribe({
      next: (data) => {
        receivedData = data;
      },
      error: (err) => receivedError = err,
    });

    // Con retry attivo, gestisce 4 tentativi
    for (let i = 0; i < 4; i++) {
      const req = httpMock.expectOne('/api/dashboard');
      req.error(new ProgressEvent('Internal Server Error'));
      if (i < 3) tick(Math.pow(2, i) * 1000);
    }

    // L'errore non deve propagarsi (catchError lo gestisce)
    expect(receivedError).toBeNull();
    expect(receivedData.engine_status).toBe('OFFLINE');
  }));
});
