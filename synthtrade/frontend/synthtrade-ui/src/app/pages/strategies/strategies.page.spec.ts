/* eslint-disable @typescript-eslint/no-explicit-any */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { StrategiesPage } from './strategies.page';
import { StrategyService } from '../../core/services/strategy.service';
import { PipelineService } from '../../core/services/pipeline.service';
import { WsService } from '../../core/services/ws.service';
import { GenerationWsService } from '../../core/services/generation-ws.service';
import { of, Subject } from 'rxjs';
import { Strategy } from '../../core/models/strategy.model';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

const mockStrategies: Strategy[] = [
  {
    id: '1', title: 'EMA Cross', template: 'ema', pair: 'BTC/USDT', timeframe: '1h',
    params: {}, score: 0.8, ai_score: null, ai_risk: null, ai_note: null,
    ai_strengths: [], ai_warnings: [], status: 'ACTIVE',
    backtest: { pnl_pct: 12, win_rate: 0.6, sharpe: 1.2, max_drawdown_pct: 5, num_trades: 20 },
    equity_curve: [], created_at: '2024-01-01', updated_at: '2024-01-01',
    budget_eur: 1000,
  },
  {
    id: '2', title: 'RSI Bounce', template: 'rsi', pair: 'ETH/USDT', timeframe: '4h',
    params: {}, score: 0.5, ai_score: null, ai_risk: null, ai_note: null,
    ai_strengths: [], ai_warnings: [], status: 'PENDING',
    backtest: null, equity_curve: [], created_at: '2024-01-02', updated_at: '2024-01-02',
    budget_eur: 1000,
  },
];

describe('StrategiesPage', () => {
  let fixture: ComponentFixture<StrategiesPage>;
  let el: HTMLElement;
  let strategyService: jest.Mocked<StrategyService>;
  let pipelineService: jest.Mocked<PipelineService>;
  let wsService: jest.Mocked<WsService>;
  let wsSubject: Subject<any>;

  let generationWsService: jest.Mocked<GenerationWsService>;
  let generationWsSubject: Subject<any>;

  beforeEach(async () => {
    wsSubject = new Subject();
    generationWsSubject = new Subject();
    strategyService = {
      getStrategies: jest.fn().mockReturnValue(of(mockStrategies)),
      approve: jest.fn().mockReturnValue(of({ id: '2', status: 'APPROVED' })),
      reject: jest.fn().mockReturnValue(of({ id: '1', status: 'REJECTED' })),
      deleteStrategy: jest.fn().mockReturnValue(of({ id: '1', status: 'DELETED' })),
      activate: jest.fn().mockReturnValue(of({ id: '1', status: 'ACTIVE' })),
      stop: jest.fn().mockReturnValue(of({ id: '1', status: 'STOPPED', closed_trades: 0 })),
      createStrategy: jest.fn().mockReturnValue(of({ ...mockStrategies[0], id: '1' })),
    } as any;
    pipelineService = {
      generateStrategies: jest.fn().mockReturnValue(of({ generation_id: 'gen1' })),
      pollGenerationStatus: jest.fn().mockReturnValue(of({ status: 'completed', results: [] })),
    } as any;
    wsService = {
      on: jest.fn().mockReturnValue(wsSubject.asObservable()),
    } as any;
    generationWsService = {
      onGenerationComplete: jest.fn().mockReturnValue(generationWsSubject.asObservable()),
    } as any;

    await TestBed.configureTestingModule({
      imports: [StrategiesPage],
      providers: [
        provideAnimations(),
        { provide: StrategyService, useValue: strategyService },
        { provide: PipelineService, useValue: pipelineService },
        { provide: WsService, useValue: wsService },
        { provide: GenerationWsService, useValue: generationWsService },
        { provide: HttpClient, useValue: { get: jest.fn(), post: jest.fn(), delete: jest.fn() } },
        { provide: Router, useValue: { navigate: jest.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StrategiesPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  it('should load and display strategies', () => {
    expect(strategyService.getStrategies).toHaveBeenCalled();
    // Nel tab GENERAZIONE, mostra solo le strategie PENDING (1 strategia)
    expect(el.querySelectorAll('.strategy-card').length).toBe(1);
  });

  it('should show empty state when no strategies', async () => {
    // Reset the testing module to allow reconfiguration for this isolated case
    await TestBed.resetTestingModule();
    const emptyStrategyService = {
      getStrategies: jest.fn().mockReturnValue(of([])),
      approve: jest.fn().mockReturnValue(of({ id: '1', status: 'APPROVED' })),
      reject: jest.fn().mockReturnValue(of({ id: '1', status: 'REJECTED' })),
      deleteStrategy: jest.fn().mockReturnValue(of({ id: '1', status: 'DELETED' })),
      activate: jest.fn().mockReturnValue(of({ id: '1', status: 'ACTIVE' })),
      stop: jest.fn().mockReturnValue(of({ id: '1', status: 'STOPPED', closed_trades: 0 })),
      createStrategy: jest.fn().mockReturnValue(of(mockStrategies[0])),
    } as any;
    const emptyPipelineService = {
      generateStrategies: jest.fn().mockReturnValue(of({ generation_id: 'gen1' })),
      pollGenerationStatus: jest.fn().mockReturnValue(of({ status: 'completed', results: [] })),
    } as any;
    const emptyWsService = {
      on: jest.fn().mockReturnValue(new Subject<any>().asObservable()),
    } as any;

    await TestBed.configureTestingModule({
      imports: [StrategiesPage],
      providers: [
        provideAnimations(),
        { provide: StrategyService, useValue: emptyStrategyService },
        { provide: PipelineService, useValue: emptyPipelineService },
        { provide: WsService, useValue: emptyWsService },
        { provide: HttpClient, useValue: { get: jest.fn(), post: jest.fn(), delete: jest.fn() } },
        { provide: Router, useValue: { navigate: jest.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StrategiesPage);
    fixture.detectChanges();
    el = fixture.nativeElement;
    
    // Cambia tab ad APPROVATE per vedere l'empty state (nel tab GENERAZIONE c'è la welcome-card)
    fixture.componentInstance.activeTab.set('APPROVATE');
    fixture.detectChanges();
    
    expect(el.querySelector('app-empty-state')).toBeTruthy();
  });

  it('should filter strategies by status tab', () => {
    const tabs = el.querySelectorAll('.tab');
    (tabs[2] as HTMLElement).click(); // ACTIVE tab (index 2 = ATTIVE)
    fixture.detectChanges();
    const rows = el.querySelectorAll('.active-row');
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

  it('should update UI on generation_complete WS message', () => {
    const comp = fixture.componentInstance as any;
    // start generation to set generationId and status
    comp.onGenerate({} as any);
    // simulate WS generation_complete
    generationWsSubject.next({
      type: 'generation_complete',
      payload: { generation_id: 'gen1', count: 2 },
    });
    fixture.detectChanges();
    expect(comp.generationResultCount()).toBe(2);
    expect(comp.generationStatus()).toBe('completed');
  });
});
