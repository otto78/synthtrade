import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { StrategyService } from './strategy.service';

const MOCK_STRATEGY = {
  id: 'trend_00001', title: 'EMA Trend', status: 'PENDING', score: 0.72,
  template: 'trend_ema', pair: 'BTC/USDT', timeframe: '5m',
  params: {}, ai_score: null, ai_risk: null, ai_note: null,
  ai_strengths: [], ai_warnings: [], backtest: null, equity_curve: [],
  created_at: '', updated_at: '',
};

describe('StrategyService', () => {
  let service: StrategyService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [StrategyService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(StrategyService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should call GET /strategies', () => {
    service.getStrategies().subscribe();
    const req = httpMock.expectOne('/api/strategies');
    expect(req.request.method).toBe('GET');
    req.flush([MOCK_STRATEGY]);
  });

  it('should call GET /strategies with status filter', () => {
    service.getStrategies('PENDING').subscribe();
    const req = httpMock.expectOne(r => r.url === '/api/strategies' && r.params.get('strategy_status') === 'PENDING');
    expect(req.request.method).toBe('GET');
    req.flush([MOCK_STRATEGY]);
  });

  it('should call GET /strategies/:id', () => {
    service.getStrategy('trend_00001').subscribe();
    const req = httpMock.expectOne('/api/strategies/trend_00001');
    expect(req.request.method).toBe('GET');
    req.flush(MOCK_STRATEGY);
  });

  it('should call POST /strategies/:id/approve', () => {
    service.approve('trend_00001').subscribe();
    const req = httpMock.expectOne('/api/strategies/trend_00001/approve');
    expect(req.request.method).toBe('POST');
    req.flush({ id: 'trend_00001', status: 'APPROVED' });
  });

  it('should call POST /strategies/:id/reject', () => {
    service.reject('trend_00001').subscribe();
    const req = httpMock.expectOne('/api/strategies/trend_00001/reject');
    expect(req.request.method).toBe('POST');
    req.flush({ id: 'trend_00001', status: 'REJECTED' });
  });
});
