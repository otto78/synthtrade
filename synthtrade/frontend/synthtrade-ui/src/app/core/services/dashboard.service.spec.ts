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
});
