import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LogsPage } from './logs.page';
import { LogService } from '../../core/services/log.service';
import { WsService } from '../../core/services/ws.service';
import { of, Subject } from 'rxjs';
import { OperationLog } from '../../core/models/log.model';
import { WsMessageType } from '../../core/models/ws-message.model';

const mockLogs: OperationLog[] = [
  { id: '1', strategy_id: 's1', action: 'BUY', price: 60000, quantity: 0.1, reason: 'signal', ai_score: 0.8, metadata: {}, created_at: '2024-01-01T10:00:00Z' },
  { id: '2', strategy_id: 's1', action: 'SELL', price: 61000, quantity: 0.1, reason: 'tp hit', ai_score: null, metadata: {}, created_at: '2024-01-01T11:00:00Z' },
  { id: '3', strategy_id: null, action: 'ERROR', price: null, quantity: null, reason: 'timeout', ai_score: null, metadata: {}, created_at: '2024-01-01T12:00:00Z' },
];

describe('LogsPage', () => {
  let fixture: ComponentFixture<LogsPage>;
  let el: HTMLElement;
  let logService: jest.Mocked<LogService>;
  let wsService: jest.Mocked<WsService>;
  let wsSubject: Subject<any>;

  beforeEach(async () => {
    wsSubject = new Subject();
    logService = {
      getLogs: jest.fn().mockReturnValue(of(mockLogs)),
    } as any;
    wsService = {
      on: jest.fn().mockReturnValue(wsSubject.asObservable()),
    } as any;

    await TestBed.configureTestingModule({
      imports: [LogsPage],
      providers: [
        { provide: LogService, useValue: logService },
        { provide: WsService, useValue: wsService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LogsPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should call getLogs on init', () => {
    expect(logService.getLogs).toHaveBeenCalled();
  });

  it('should render log rows', () => {
    expect(el.querySelectorAll('.log-row').length).toBe(3);
  });

  it('should filter logs by action level', () => {
    const select = el.querySelector('select.filter-level') as HTMLSelectElement;
    select.value = 'BUY';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(logService.getLogs).toHaveBeenCalledWith(expect.objectContaining({ action: 'BUY' }));
  });

  it('should prepend new log on WS new_log message', () => {
    const newLog: OperationLog = { id: '99', strategy_id: null, action: 'SKIP', price: null, quantity: null, reason: 'ws', ai_score: null, metadata: {}, created_at: new Date().toISOString() };
    wsSubject.next({ type: WsMessageType.NewLog, payload: newLog });
    fixture.detectChanges();
    expect(fixture.componentInstance.logs()[0].id).toBe('99');
  });

  it('should load next page on pagination click', () => {
    const nextBtn = el.querySelector('.btn-next') as HTMLElement;
    nextBtn.click();
    expect(logService.getLogs).toHaveBeenCalledWith(expect.objectContaining({ offset: 50 }));
  });
});
