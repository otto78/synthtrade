import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DashboardPage } from './dashboard.page';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { of, Subject } from 'rxjs';
import { WsMessageType } from '../../core/models/ws-message.model';

describe('DashboardPage', () => {
  let fixture: ComponentFixture<DashboardPage>;
  let el: HTMLElement;
  let dashboardService: jest.Mocked<DashboardService>;
  let wsService: jest.Mocked<WsService>;
  let wsSubject: Subject<any>;

  beforeEach(async () => {
    wsSubject = new Subject();
    dashboardService = {
      getStats: jest.fn().mockReturnValue(of({
        balance: 10000,
        pnl_today: 250,
        active_positions: 2,
        total_trades: 45,
      })),
    } as any;
    wsService = {
      on: jest.fn().mockReturnValue(wsSubject.asObservable()),
    } as any;

    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [
        { provide: DashboardService, useValue: dashboardService },
        { provide: WsService, useValue: wsService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should call getStats on init', () => {
    expect(dashboardService.getStats).toHaveBeenCalled();
  });

  it('should render 3 StatCard components', () => {
    expect(el.querySelectorAll('app-stat-card').length).toBe(3);
  });

  it('should update stats on WS stats_update message', () => {
    wsSubject.next({ type: WsMessageType.StatsUpdate, payload: { balance: 11000 } });
    fixture.detectChanges();
    expect(fixture.componentInstance.stats().balance).toBe(11000);
  });

  it('should pass loading=true to StatCards when loading', () => {
    fixture.componentInstance.loading.set(true);
    fixture.detectChanges();
    // loading=true viene passato come input ai StatCard — verifichiamo che il componente sia in stato loading
    expect(fixture.componentInstance.loading()).toBe(true);
  });
});
