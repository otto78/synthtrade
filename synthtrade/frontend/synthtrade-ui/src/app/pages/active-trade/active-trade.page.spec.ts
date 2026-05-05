import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActiveTradePage } from './active-trade.page';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { of, Subject } from 'rxjs';
import { WsMessageType } from '../../core/models/ws-message.model';

describe('ActiveTradePage', () => {
  let fixture: ComponentFixture<ActiveTradePage>;
  let el: HTMLElement;
  let dashboardService: jest.Mocked<DashboardService>;
  let wsService: jest.Mocked<WsService>;
  let wsSubject: Subject<any>;

  const mockStats = {
    balance: 10000, pnl_today: 100,
    active_strategy: { id: 's1', title: 'EMA Cross', pair: 'BTC/USDT' },
    engine_status: 'RUNNING',
  };

  beforeEach(async () => {
    wsSubject = new Subject();
    dashboardService = {
      getStats: jest.fn().mockReturnValue(of(mockStats)),
    } as any;
    wsService = {
      on: jest.fn().mockReturnValue(wsSubject.asObservable()),
    } as any;

    await TestBed.configureTestingModule({
      imports: [ActiveTradePage],
      providers: [
        { provide: DashboardService, useValue: dashboardService },
        { provide: WsService, useValue: wsService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ActiveTradePage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should show empty state when no active strategy', () => {
    dashboardService.getStats.mockReturnValue(of({ ...mockStats, active_strategy: null }));
    fixture = TestBed.createComponent(ActiveTradePage);
    fixture.detectChanges();
    el = fixture.nativeElement;
    expect(el.querySelector('app-empty-state')).toBeTruthy();
  });

  it('should render active trade info when strategy present', () => {
    expect(el.querySelector('.trade-title')?.textContent).toContain('EMA Cross');
    expect(el.querySelector('.trade-pair')?.textContent).toContain('BTC/USDT');
  });

  it('should update price on WS price_update message', () => {
    wsSubject.next({ type: WsMessageType.Price, payload: { pair: 'BTC/USDT', price: 65000 } });
    fixture.detectChanges();
    expect(fixture.componentInstance.currentPrice()).toBe(65000);
  });

  it('should apply positive class when pnl > 0', () => {
    fixture.componentInstance.pnl.set(5.5);
    fixture.detectChanges();
    expect(el.querySelector('.pnl')?.classList).toContain('positive');
  });

  it('should apply negative class when pnl < 0', () => {
    fixture.componentInstance.pnl.set(-3.2);
    fixture.detectChanges();
    expect(el.querySelector('.pnl')?.classList).toContain('negative');
  });
});
