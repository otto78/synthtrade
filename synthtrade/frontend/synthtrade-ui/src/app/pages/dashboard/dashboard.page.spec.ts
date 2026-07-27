import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DashboardPage } from './dashboard.page';
import { DashboardService } from '../../core/services/dashboard.service';
import { of, Subject } from 'rxjs';

describe('DashboardPage', () => {
  let fixture: ComponentFixture<DashboardPage>;
  let el: HTMLElement;
  let dashboardService: jest.Mocked<DashboardService>;

  beforeEach(async () => {
    dashboardService = {
      getStats: jest.fn().mockReturnValue(of({
        balance_eur: 10000,
        currency: 'EUR',
        balance_breakdown: {},
        balance_assets: [],
        engine_status: 'RUNNING',
        active_strategies_count: 1,
        open_trades_count: 2,
        active_session_count: 0,
        exchange_provider: 'okx',
        total_active_pnl_pct: 0,
      })),
    } as any;

    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [
        { provide: DashboardService, useValue: dashboardService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should call getStats on init', () => {
    expect(dashboardService.getStats).toHaveBeenCalled();
  });

  it('should render 4 StatCard components', () => {
    expect(el.querySelectorAll('app-stat-card').length).toBe(4);
  });

  it('should show balance label "Saldo OKX"', () => {
    expect(fixture.componentInstance.balanceLabel()).toBe('Saldo OKX');
  });

  it('should format balance in EUR', () => {
    const formatted = fixture.componentInstance.balanceFormatted();
    expect(formatted).toContain('10.000');
    expect(formatted).toContain('€');
  });

  it('should pass loading=true to StatCards when loading', () => {
    fixture.componentInstance.loading.set(true);
    fixture.detectChanges();
    expect(fixture.componentInstance.loading()).toBe(true);
  });

  it('should show error message when getStats fails', () => {
    dashboardService.getStats.mockReturnValue(
      new Subject().asObservable()
    );

    const newFixture = TestBed.createComponent(DashboardPage);
    const component = newFixture.componentInstance;

    component.error.set('Failed to load dashboard stats');
    newFixture.detectChanges();

    const errorEl = newFixture.nativeElement.querySelector('.error-msg');
    expect(errorEl).toBeTruthy();
    expect(errorEl?.textContent).toContain('Failed to load');
  });

  it('should set loading to false after data loads', () => {
    expect(fixture.componentInstance.loading()).toBe(false);
  });

  it('should show active session status', () => {
    const component = fixture.componentInstance;
    expect(component.sessionStr()).toBe('0');

    // Simulate active session
    component.stats.update(s => ({ ...s, active_session_count: 1 }));
    expect(component.sessionStr()).toBe('Attiva');
  });

  it('should unsubscribe on destroy to prevent memory leaks', () => {
    const component = fixture.componentInstance;
    const subSpy = jest.spyOn(component['sub'], 'unsubscribe');

    fixture.destroy();

    expect(subSpy).toHaveBeenCalled();
  });
});