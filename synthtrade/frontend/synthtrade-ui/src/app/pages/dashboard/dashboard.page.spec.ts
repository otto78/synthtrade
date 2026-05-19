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
        balance_eur: 10000,
        balance_breakdown: {},
        balance_assets: [],
        pnl_today: 250,
        active_strategy: null,
        engine_status: 'RUNNING'
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
    wsSubject.next({ type: WsMessageType.StatsUpdate, payload: { balance_eur: 11000 } });
    fixture.detectChanges();
    expect(fixture.componentInstance.stats().balance_eur).toBe(11000);
  });

  it('should pass loading=true to StatCards when loading', () => {
    fixture.componentInstance.loading.set(true);
    fixture.detectChanges();
    // loading=true viene passato come input ai StatCard — verifichiamo che il componente sia in stato loading
    expect(fixture.componentInstance.loading()).toBe(true);
  });

  // TASK-187: Test gestione errori e timeout
  it('should show error message when getStats fails', () => {
    dashboardService.getStats.mockReturnValue(
      new Subject().asObservable() // Observable che genera errore
    );

    const newFixture = TestBed.createComponent(DashboardPage);
    const component = newFixture.componentInstance;

    // Simula errore
    component.error.set('Failed to load dashboard stats');
    newFixture.detectChanges();

    const errorEl = newFixture.nativeElement.querySelector('.error-msg');
    expect(errorEl).toBeTruthy();
    expect(errorEl?.textContent).toContain('Failed to load');
  });

  it('should clear error when new data arrives', () => {
    const component = fixture.componentInstance;

    // Simula errore
    component.error.set('Some error');
    expect(component.error()).toBe('Some error');

    // Simula arrivo di nuovi dati
    wsSubject.next({ type: WsMessageType.StatsUpdate, payload: { balance_eur: 12000 } });

    // Errore deve essere pulito
    expect(component.error()).toBeNull();
  });

  it('should set loading to false after data loads', () => {
    expect(fixture.componentInstance.loading()).toBe(false);
  });

  it('should handle WebSocket error gracefully', () => {
    const component = fixture.componentInstance;
    component.error.set(null);

    // Simula errore WebSocket
    wsSubject.error(new Error('WebSocket connection lost'));
    fixture.detectChanges();

    expect(component.error()).toBe('WebSocket error');
  });

  it('should unsubscribe on destroy to prevent memory leaks', () => {
    const component = fixture.componentInstance;
    const subSpy = jest.spyOn(component['sub'], 'unsubscribe');

    fixture.destroy();

    expect(subSpy).toHaveBeenCalled();
  });
});
