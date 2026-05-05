import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StrategiesPage } from './strategies.page';
import { StrategyService } from '../../core/services/strategy.service';
import { of } from 'rxjs';
import { Strategy } from '../../core/models/strategy.model';

const mockStrategies: Strategy[] = [
  {
    id: '1', title: 'EMA Cross', template: 'ema', pair: 'BTC/USDT', timeframe: '1h',
    params: {}, score: 0.8, ai_score: null, ai_risk: null, ai_note: null,
    ai_strengths: [], ai_warnings: [], status: 'ACTIVE',
    backtest: { pnl_pct: 12, win_rate: 0.6, sharpe: 1.2, max_drawdown_pct: 5, num_trades: 20 },
    equity_curve: [], created_at: '2024-01-01', updated_at: '2024-01-01',
  },
  {
    id: '2', title: 'RSI Bounce', template: 'rsi', pair: 'ETH/USDT', timeframe: '4h',
    params: {}, score: 0.5, ai_score: null, ai_risk: null, ai_note: null,
    ai_strengths: [], ai_warnings: [], status: 'PENDING',
    backtest: null, equity_curve: [], created_at: '2024-01-02', updated_at: '2024-01-02',
  },
];

describe('StrategiesPage', () => {
  let fixture: ComponentFixture<StrategiesPage>;
  let el: HTMLElement;
  let strategyService: jest.Mocked<StrategyService>;

  beforeEach(async () => {
    strategyService = {
      getStrategies: jest.fn().mockReturnValue(of(mockStrategies)),
      approve: jest.fn().mockReturnValue(of({ id: '2', status: 'APPROVED' })),
      reject: jest.fn().mockReturnValue(of({ id: '1', status: 'REJECTED' })),
    } as any;

    await TestBed.configureTestingModule({
      imports: [StrategiesPage],
      providers: [{ provide: StrategyService, useValue: strategyService }],
    }).compileComponents();

    fixture = TestBed.createComponent(StrategiesPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should load and display strategies', () => {
    expect(strategyService.getStrategies).toHaveBeenCalled();
    expect(el.querySelectorAll('.strategy-row').length).toBe(2);
  });

  it('should show empty state when no strategies', () => {
    strategyService.getStrategies.mockReturnValue(of([]));
    fixture = TestBed.createComponent(StrategiesPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
    expect(el.querySelector('app-empty-state')).toBeTruthy();
  });

  it('should filter strategies by status tab', () => {
    const tabs = el.querySelectorAll('.tab');
    (tabs[1] as HTMLElement).click(); // ACTIVE tab
    fixture.detectChanges();
    const rows = el.querySelectorAll('.strategy-row');
    expect(rows.length).toBe(1);
  });

  it('should call approve when approve button clicked', () => {
    const approveBtn = el.querySelector('.btn-approve') as HTMLElement;
    approveBtn.click();
    expect(strategyService.approve).toHaveBeenCalled();
  });

  it('should show confirm dialog before delete/reject', () => {
    const rejectBtn = el.querySelector('.btn-reject') as HTMLElement;
    rejectBtn.click();
    fixture.detectChanges();
    expect(el.querySelector('app-confirm-dialog')).toBeTruthy();
  });
});
