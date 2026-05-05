import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { LogService } from './log.service';

describe('LogService', () => {
  let service: LogService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [LogService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(LogService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should call GET /logs with no filters', () => {
    service.getLogs({}).subscribe();
    const req = httpMock.expectOne(r => r.url === '/api/logs');
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('should serialize action filter as query param', () => {
    service.getLogs({ action: 'BUY' }).subscribe();
    const req = httpMock.expectOne(r => r.params.get('action') === 'BUY');
    req.flush([]);
  });

  it('should serialize limit and offset as query params', () => {
    service.getLogs({ limit: 10, offset: 20 }).subscribe();
    const req = httpMock.expectOne(r =>
      r.params.get('limit') === '10' && r.params.get('offset') === '20'
    );
    req.flush([]);
  });

  it('should serialize strategy_id filter', () => {
    service.getLogs({ strategy_id: 'trend_00001' }).subscribe();
    const req = httpMock.expectOne(r => r.params.get('strategy_id') === 'trend_00001');
    req.flush([]);
  });

  it('should call GET /logs/export', () => {
    service.exportCsv().subscribe();
    const req = httpMock.expectOne('/api/logs/export');
    expect(req.request.method).toBe('GET');
    req.flush('id,action\n');
  });
});
