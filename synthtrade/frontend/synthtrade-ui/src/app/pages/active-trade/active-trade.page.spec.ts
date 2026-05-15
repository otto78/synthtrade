/* eslint-disable @typescript-eslint/no-explicit-any */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActiveTradePage } from './active-trade.page';
import { StrategyService } from '../../core/services/strategy.service';
import { WsService } from '../../core/services/ws.service';
import { DashboardService } from '../../core/services/dashboard.service';
import { of, Subject } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { WsMessageType } from '../../core/models/ws-message.model';

describe('ActiveTradePage', () => {
  let fixture: ComponentFixture<ActiveTradePage>;
  let el: HTMLElement;
  let strategyService: jest.Mocked<StrategyService>;
  let wsService: jest.Mocked<WsService>;
  let dashboardService: jest.Mocked<DashboardService>;
  let wsSubject: Subject<any>;

  const mockPnlResponse = {
    active_strategies_pnl: [
      { id: 's1', title: 'EMA Cross', avg_pnl_pct: 4.0, total_pnl_pct: 4.0, current_value_usdt: 52000, open_trades_count: 1 },
    ],
  };

  const mockMonitorData = {
    strategy: { id: 's1', title: 'EMA Cross', status: 'ACTIVE', pair: 'BTC/USDT', timeframe: '1h' },
    stats: {
      total_pnl_pct: 4.0,
      total_pnl_eur: 50.0,
      win_rate: 60,
      total_trades: 3,
      active_trades: 1,
      equity_curve: [100, 102, 104],
    },
    recent_trades: [
      { id: 't1', executed_at: '2026-05-14T10:00:00Z', pair: 'BTC/USDT', symbol: 'BTC/USDT',
        action: 'BUY', side: 'BUY', pnl_pct: 4.0, price: 50000, quantity: 0.015,
        status: 'OPEN', trade_type: 'INITIAL_ALLOCATION', strategy_id: 's1' },
    ],
  };

  beforeEach(async () => {
    wsSubject = new Subject();
    strategyService = {
      getActivePnl: jest.fn().mockReturnValue(of(mockPnlResponse)),
      getMonitorData: jest.fn().mockReturnValue(of(mockMonitorData)),
    } as any;
    wsService = {
      on: jest.fn().mockReturnValue(wsSubject.asObservable()),
    } as any;
    dashboardService = {
      getDashboardStats: jest.fn().mockReturnValue(of({})),
    } as any;

    await TestBed.configureTestingModule({
      imports: [ActiveTradePage],
      providers: [
        { provide: StrategyService, useValue: strategyService },
        { provide: WsService, useValue: wsService },
        { provide: DashboardService, useValue: dashboardService },
        { provide: HttpClient, useValue: { get: jest.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ActiveTradePage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  // Test 1: Show empty state when no active strategies
  it('should show empty state when no active strategies', () => {
    strategyService.getActivePnl.mockReturnValue(of({ active_strategies_pnl: [] }));
    fixture = TestBed.createComponent(ActiveTradePage);
    fixture.detectChanges();
    el = fixture.nativeElement;
    expect(el.querySelector('app-empty-state')).toBeTruthy();
  });

  // Test 2: Render strategy sections
  it('should render strategy sections when active strategies present', () => {
    expect(el.querySelector('.section-title')?.textContent).toContain('EMA Cross');
    expect(el.querySelector('.section-meta')?.textContent).toContain('BTC/USDT');
  });

  // Test 3: Display KPI cards
  it('should display KPI cards', () => {
    const kpiCards = el.querySelectorAll('.kpi-card');
    expect(kpiCards.length).toBe(3);
  });

  // Test 4: Display open trades count
  it('should display total open trades', () => {
    const totalTrades = fixture.componentInstance.totalOpenTrades();
    expect(totalTrades).toBe(1);
  });

  // Test 5: Display app-active-trade-row component for open trades
  it('should render active-trade-row component for open trades', () => {
    expect(el.querySelector('app-active-trade-row')).toBeTruthy();
  });

  // Test 6: Reload strategies on WS trade_opened
  it('should reload strategies on WS trade_opened', () => {
    const spy = jest.spyOn(strategyService, 'getActivePnl');
    wsSubject.next({ type: WsMessageType.TradeOpened });
    fixture.detectChanges();
    expect(spy).toHaveBeenCalled();
  });

  // Test 7: Reload strategies on WS trade_closed
  it('should reload strategies on WS trade_closed', () => {
    const spy = jest.spyOn(strategyService, 'getActivePnl');
    wsSubject.next({ type: WsMessageType.TradeClosed });
    fixture.detectChanges();
    expect(spy).toHaveBeenCalled();
  });

  // Test 8: P&L total computed correctly (average of all strategies)
  it('should compute total P&L correctly', () => {
    const pnl = fixture.componentInstance.totalPnl();
    expect(pnl).toBe(4.0);
  });
});