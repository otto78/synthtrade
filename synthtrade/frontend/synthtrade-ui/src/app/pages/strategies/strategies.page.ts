import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { StrategyService } from '../../core/services/strategy.service';
import { PipelineService } from '../../core/services/pipeline.service';
import { Strategy, StrategyRequest, GenerationStatus, GenerationProgressStatus, StrategyCreateDto } from '../../core/models/strategy.model';
import { BadgeStatusComponent } from '../../shared/components/badge-status/badge-status.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { StrategyRequestFormComponent } from '../../shared/components/strategy-request-form/strategy-request-form.component';
import { GenerationProgressComponent } from '../../shared/components/generation-progress/generation-progress.component';
import { NgClass, KeyValuePipe, DecimalPipe, CurrencyPipe, DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { switchMap } from 'rxjs';
import { animate, style, transition, trigger } from '@angular/animations';

type Tab = 'GENERAZIONE' | 'APPROVATE' | 'ATTIVE' | 'COMPLETATE';

@Component({
  selector: 'app-strategies',
  standalone: true,
  imports: [
    BadgeStatusComponent, 
    ConfirmDialogComponent, 
    EmptyStateComponent, 
    StrategyRequestFormComponent,
    GenerationProgressComponent,
    NgClass,
    KeyValuePipe,
    DecimalPipe,
    CurrencyPipe,
    DatePipe
  ],
  animations: [
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('300ms ease-out', style({ opacity: 1 }))
      ])
    ]),
    trigger('slideIn', [
      transition(':enter', [
        style({ transform: 'translateY(20px)', opacity: 0 }),
        animate('300ms ease-out', style({ transform: 'translateY(0)', opacity: 1 }))
      ])
    ])
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="strategies">
      <div class="header-actions">
        <h1 class="page-title">Gestione Strategie</h1>
        <div class="tabs">
          @for (tab of tabs; track tab) {
            <button class="tab" [ngClass]="{ 'tab--active': activeTab() === tab }" (click)="activeTab.set(tab)">
              {{ tab }}
              @if (countForTab(tab) > 0) {
                <span class="tab-badge">{{ countForTab(tab) }}</span>
              }
            </button>
          }
        </div>
      </div>

      <div class="content-area">
        <!-- FASE 1: GENERAZIONE -->
        @if (activeTab() === 'GENERAZIONE') {
          <div class="generation-container">
            @if (!generationId()) {
              <div class="welcome-card">
                <h2>Crea nuove strategie con AI</h2>
                <p>Inserisci i tuoi parametri e lascia che l'intelligenza artificiale trovi i pattern migliori per te.</p>
                <app-strategy-request-form (requestSubmitted)="onGenerate($event)" />
              </div>
            } @else {
              <app-generation-progress [status]="generationStatus()" />
              
              @if (generationStatus() === 'completed') {
                <div class="generated-results" @fadeIn>
                  <div class="results-header">
                    <h3 class="results-title">✨ Strategie Candidate</h3>
                    <button class="btn-new-search-inline" (click)="resetGeneration()">
                      <span class="icon">🔍</span> Nuova Ricerca
                    </button>
                  </div>
                  
                  <div class="strategy-grid">
                    @for (s of generatedStrategies(); track $index) {
                      <div class="strategy-card" @slideIn>
                        <div class="card-header">
                          <div class="title-group">
                            <div class="ai-badge">✨ AI Optimized</div>
                            <span class="strategy-name">{{ s.title }}</span>
                            <div class="meta-tags">
                              <span class="tag tag--pair">{{ s.pair }}</span>
                              <span class="tag tag--tf">{{ s.timeframe }}</span>
                            </div>
                          </div>
                          <div class="profit-estimate">
                            <span class="profit-label">Profitto Stimato</span>
                            <span class="profit-value success">
                              +{{ (s.estimated_profit_pct || 0) | number:'1.1-2' }}%
                            </span>
                            <span class="profit-abs">
                              ≈ {{ (s.estimated_profit_eur || 0) | currency:'EUR':'symbol':'1.2-2' }}
                            </span>
                          </div>
                          @if (s.expires_at) {
                            <div class="expiry-timer">
                              <span class="timer-label">Scade il</span>
                              <span class="timer-value">{{ s.expires_at | date:'dd/MM HH:mm' }}</span>
                            </div>
                          }
                        </div>

                        <p class="strategy-description">{{ s.description }}</p>

                        <div class="params-list">
                          @for (param of s.params | keyvalue; track param.key) {
                            <div class="param-row">
                              <span class="param-dot"></span>
                              <span class="param-label">{{ formatParamLabel(param.key) }}:</span>
                              <span class="param-value">{{ formatParamValue(param.key, param.value) }}</span>
                            </div>
                          }
                        </div>

                        <div class="card-actions">
                          <button class="btn-approve" (click)="saveAndApprove(s)">
                            <span class="icon">✅</span> Approva
                          </button>
                          <button class="btn-reject" (click)="removeGenerated(s)">
                            <span class="icon">🗑️</span> Scarta
                          </button>
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }
            }
          </div>
        }

        <!-- FASE 2: APPROVATE (PENDING START) -->
        @if (activeTab() === 'APPROVATE') {
          <div class="approved-container" @fadeIn>
            @if (approved().length === 0) {
              <app-empty-state message="Nessuna strategia in attesa di avvio. Generane una nuova!" />
            } @else {
              <div class="strategy-grid">
                @for (s of approved(); track s.id) {
                  <div class="strategy-card approved" @slideIn>
                    <div class="card-header">
                      <div class="title-group">
                        <span class="strategy-name">{{ s.title }}</span>
                        <div class="meta-tags">
                          <span class="tag tag--pair">{{ s.pair }}</span>
                          <span class="tag tag--tf">{{ s.timeframe }}</span>
                        </div>
                      </div>
                      <app-badge-status [status]="s.status" />
                    </div>
                    
                    <div class="card-actions">
                      <button class="btn-start" (click)="startStrategy(s)">
                        <span class="icon">🚀</span> Avvia Esecuzione
                      </button>
                      <button class="btn-reject-ghost" (click)="confirmReject(s)">Rifiuta</button>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        }

        <!-- FASE 3: ATTIVE -->
        @if (activeTab() === 'ATTIVE') {
          <div class="active-container" @fadeIn>
            @if (active().length === 0) {
              <app-empty-state message="Nessuna strategia attualmente in esecuzione." />
            } @else {
              <div class="active-list">
                @for (s of active(); track s.id) {
                  <div class="active-row" @slideIn>
                    <div class="active-info">
                      <span class="active-title">{{ s.title }}</span>
                      <span class="active-meta">{{ s.pair }} · {{ s.timeframe }}</span>
                    </div>
                    <div class="active-status">
                      <span class="pulse-dot"></span>
                      In Esecuzione
                    </div>
                    <div class="active-actions">
                      <button class="btn-view" (click)="goToDetail(s)">Monitora</button>
                      <button class="btn-stop" (click)="stopStrategy(s)">Stop</button>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        }

        <!-- FASE 4 & 5: COMPLETATE & VALUTAZIONE -->
        @if (activeTab() === 'COMPLETATE') {
          <div class="completed-container" @fadeIn>
            @if (completed().length === 0) {
              <app-empty-state message="Non ci sono strategie completate nella cronologia." />
            } @else {
              <div class="accordion-list">
                @for (s of completed(); track s.id) {
                  <div class="accordion-item" [class.accordion-item--expanded]="expandedStrategy() === s.id" @slideIn>
                    <!-- Header Accordion -->
                    <div class="accordion-header" (click)="toggleExpand(s.id!)">
                      <div class="acc-info">
                        <span class="acc-title">{{ s.title }}</span>
                        <div class="acc-meta">
                          <span class="tag">{{ s.pair }}</span>
                          <span class="date">{{ s.updated_at | date:'dd MMM yyyy' }}</span>
                        </div>
                      </div>
                      <div class="acc-stats">
                        <div class="stat-group">
                          <span class="label">P&L Totale</span>
                          <span class="value" [class.success]="(s.backtest?.pnl_pct || 0) > 0">
                            {{ (s.backtest?.pnl_pct || 0) | number:'1.2-2' }}%
                          </span>
                        </div>
                        <div class="stat-group">
                          <span class="label">Win Rate</span>
                          <span class="value">{{ (s.backtest?.win_rate || 0) | number:'1.0-0' }}%</span>
                        </div>
                      </div>
                      <span class="chevron"></span>
                    </div>

                    <!-- Content Accordion (Dettaglio) -->
                    @if (expandedStrategy() === s.id) {
                      <div class="accordion-content" @fadeIn>
                        <div class="detail-grid">
                          <div class="detail-card">
                            <h4>Statistiche Dettagliate</h4>
                            <div class="mini-stats">
                              <div class="ms-row"><span>Max Drawdown</span><span class="danger">{{ s.backtest?.max_drawdown_pct | number:'1.1-2' }}%</span></div>
                              <div class="ms-row"><span>Sharpe Ratio</span><span>{{ s.backtest?.sharpe | number:'1.2-2' }}</span></div>
                              <div class="ms-row"><span>Totale Trade</span><span>{{ s.backtest?.num_trades }}</span></div>
                            </div>
                          </div>
                          <div class="detail-card">
                            <h4>Equity Curve</h4>
                            <div class="equity-preview">
                              <!-- Placeholder grafico a barre per performance -->
                              <div class="bars">
                                @for (val of s.equity_curve; track $index) {
                                  <div class="bar" [style.height.%]="val * 100"></div>
                                }
                              </div>
                            </div>
                          </div>
                        </div>

                        <div class="accordion-actions">
                          <button class="btn-outline" (click)="goToDetail(s)">Vedi Analisi Completa</button>
                          <button class="btn-outline btn-export">
                            <span class="icon">📥</span> Esporta Report
                          </button>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            }
          </div>
        }
      </div>

      <app-confirm-dialog
        [visible]="!!pendingReject()"
        message="Sei sicuro di voler scartare questa strategia?"
        (confirmed)="doReject()"
        (cancelled)="pendingReject.set(null)"
      />

      <app-confirm-dialog
        [visible]="!!pendingStop()"
        message="Sei sicuro di voler interrompere questa strategia attiva? L'operazione è irreversibile."
        (confirmed)="doStop()"
        (cancelled)="pendingStop.set(null)"
      />
    </div>
  `,
  styles: [`
    .strategies { padding: 24px; max-width: 1200px; margin: 0 auto; }
    .page-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0; }
    .header-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; border-bottom: 1px solid var(--border-default); padding-bottom: 16px; }
    
    .tabs { display: flex; gap: 4px; background: var(--bg-surface); padding: 4px; border-radius: 8px; }
    .tab { 
      background: none; border: none; color: var(--text-secondary); 
      padding: 8px 20px; border-radius: 6px; cursor: pointer; 
      font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px;
      transition: all 0.2s;
    }
    .tab--active { background: var(--bg-elevated); color: var(--accent-primary); box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .tab-badge { background: var(--accent-primary); color: #000; font-size: 10px; padding: 2px 6px; border-radius: 10px; }

    .welcome-card { background: var(--bg-card); padding: 40px; border-radius: 16px; border: 1px dashed var(--border-default); text-align: center; max-width: 600px; margin: 40px auto; }
    .welcome-card h2 { margin-bottom: 12px; color: var(--text-primary); }
    .welcome-card p { color: var(--text-secondary); margin-bottom: 32px; }

    .results-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
    
    .btn-new-search-inline { 
      background: rgba(240, 185, 11, 0.1); 
      color: var(--accent-primary); 
      border: 1px solid var(--accent-primary); 
      padding: 8px 16px; 
      border-radius: 8px; 
      font-size: 13px; 
      font-weight: 600; 
      cursor: pointer; 
      display: flex; 
      align-items: center; 
      gap: 8px;
      transition: all 0.2s;
    }
    .btn-new-search-inline:hover { background: var(--accent-primary); color: #000; }

    .strategy-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 24px; }
    .strategy-card { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 16px; transition: all 0.2s; }
    .strategy-card:hover { border-color: var(--accent-primary); transform: translateY(-4px); }

    .strategy-description { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0; }

    .params-list { display: flex; flex-direction: column; gap: 8px; background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; }
    .param-row { display: flex; align-items: center; gap: 8px; }
    .param-dot { width: 4px; height: 4px; background: var(--accent-primary); border-radius: 50%; }
    .param-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
    .param-value { font-size: 12px; color: var(--text-primary); font-weight: 700; font-family: monospace; }

    .card-actions { display: flex; gap: 12px; margin-top: auto; padding-top: 16px; border-top: 1px solid var(--border-default); }
    .btn-approve, .btn-start { flex: 2; background: var(--color-buy); color: #000; border: none; padding: 10px; border-radius: 6px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; }
    .btn-reject { flex: 1; background: rgba(246,70,93,0.1); color: var(--color-sell); border: 1px solid var(--color-sell); padding: 10px; border-radius: 6px; cursor: pointer; }
    .btn-reject-ghost { flex: 1; background: transparent; color: var(--text-secondary); border: 1px solid var(--border-default); padding: 10px; border-radius: 6px; cursor: pointer; }
    
    .profit-estimate { text-align: right; }
    .profit-label { display: block; font-size: 9px; color: var(--text-secondary); text-transform: uppercase; }
    .profit-value { font-size: 18px; font-weight: 700; color: var(--color-buy); }
    .profit-abs { display: block; font-size: 11px; color: var(--text-secondary); font-family: monospace; }

    .expiry-timer { text-align: right; background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); }
    .timer-label { display: block; font-size: 8px; color: var(--text-secondary); text-transform: uppercase; }
    .timer-value { font-size: 11px; font-weight: 600; color: var(--accent-primary); font-family: monospace; }

    .active-list { display: flex; flex-direction: column; gap: 12px; }
    .active-row { background: var(--bg-card); border: 1px solid var(--border-default); padding: 16px 24px; border-radius: 12px; display: flex; align-items: center; gap: 24px; }
    .active-info { flex: 1; }
    .active-title { display: block; font-size: 16px; font-weight: 600; color: var(--text-primary); }
    .active-meta { font-size: 13px; color: var(--text-secondary); font-family: monospace; }
    .active-status { display: flex; align-items: center; gap: 8px; color: var(--color-buy); font-size: 14px; font-weight: 600; }
    .pulse-dot { width: 8px; height: 8px; background: var(--color-buy); border-radius: 50%; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    .btn-view { background: var(--bg-elevated); color: var(--text-primary); border: 1px solid var(--border-default); padding: 6px 16px; border-radius: 6px; cursor: pointer; }
    .btn-stop { background: rgba(246,70,93,0.1); color: var(--color-sell); border: 1px solid var(--color-sell); padding: 6px 16px; border-radius: 6px; cursor: pointer; }

    /* Accordion Styles */
    .accordion-list { display: flex; flex-direction: column; gap: 12px; }
    .accordion-item { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 12px; overflow: hidden; transition: all 0.2s; }
    .accordion-item--expanded { border-color: var(--accent-primary); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    
    .accordion-header { padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; transition: background 0.2s; }
    .accordion-header:hover { background: rgba(255,255,255,0.02); }
    
    .acc-info { display: flex; flex-direction: column; gap: 4px; }
    .acc-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
    .acc-meta { display: flex; align-items: center; gap: 12px; }
    .acc-meta .tag { font-size: 11px; color: var(--text-secondary); font-family: monospace; background: rgba(0,0,0,0.2); padding: 2px 8px; border-radius: 4px; }
    .acc-meta .date { font-size: 11px; color: var(--text-muted); }
    
    .acc-stats { display: flex; gap: 32px; }
    .stat-group { display: flex; flex-direction: column; gap: 2px; }
    .stat-group .label { font-size: 9px; color: var(--text-muted); text-transform: uppercase; }
    .stat-group .value { font-size: 15px; font-weight: 700; font-family: monospace; }
    
    .chevron { width: 20px; height: 20px; position: relative; }
    .chevron::before { content: ''; position: absolute; top: 50%; left: 50%; width: 8px; height: 8px; border-right: 2px solid var(--text-secondary); border-bottom: 2px solid var(--text-secondary); transform: translate(-50%, -70%) rotate(45deg); transition: transform 0.3s; }
    .accordion-item--expanded .chevron::before { transform: translate(-50%, -30%) rotate(-135deg); border-color: var(--accent-primary); }

    .accordion-content { padding: 24px; border-top: 1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.1); }
    .detail-grid { display: grid; grid-template-columns: 1fr 2fr; gap: 24px; margin-bottom: 24px; }
    .detail-card { background: var(--bg-surface); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03); }
    .detail-card h4 { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin: 0 0 16px 0; }
    
    .mini-stats { display: flex; flex-direction: column; gap: 12px; }
    .ms-row { display: flex; justify-content: space-between; font-size: 13px; }
    .ms-row .danger { color: var(--color-sell); }
    
    .equity-preview { height: 100px; display: flex; align-items: flex-end; }
    .bars { display: flex; align-items: flex-end; gap: 4px; height: 100%; width: 100%; }
    .bar { flex: 1; background: var(--accent-primary); opacity: 0.5; border-radius: 2px 2px 0 0; min-width: 4px; }

    .accordion-actions { display: flex; gap: 12px; }
    .btn-outline { background: transparent; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s; }
    .btn-outline:hover { border-color: var(--text-primary); color: var(--text-primary); }
    .btn-export { color: var(--accent-primary); border-color: rgba(240,185,11,0.3); }
    .btn-export:hover { background: rgba(240,185,11,0.1); }

    .results-comparison { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; }
    .res-item { display: flex; flex-direction: column; gap: 4px; }
    .res-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; }
    .res-value { font-size: 14px; font-weight: 700; }
    .success { color: var(--color-buy); }
    .result-badge { padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; background: rgba(246,70,93,0.1); color: var(--color-sell); }
    .result-badge.success { background: rgba(14,203,129,0.1); color: var(--color-buy); }
    .btn-ghost-full { width: 100%; margin-top: 12px; background: transparent; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 8px; border-radius: 6px; cursor: pointer; }
  `]
})
export class StrategiesPage implements OnInit {
  private strategyService = inject(StrategyService);
  private pipelineService = inject(PipelineService);
  private router = inject(Router);

  readonly tabs: Tab[] = ['GENERAZIONE', 'APPROVATE', 'ATTIVE', 'COMPLETATE'];
  activeTab = signal<Tab>('GENERAZIONE');
  
  // State
  strategies = signal<Strategy[]>([]);
  generatedStrategies = signal<Strategy[]>([]);
  loading = signal(true);
  
  // Generation State
  generationId = signal<string | null>(null);
  generationStatus = signal<GenerationProgressStatus>('pending');
  
  // Dialogs
  pendingReject = signal<Strategy | null>(null);
  pendingStop = signal<Strategy | null>(null);
  expandedStrategy = signal<string | null>(null);

  // Computed State (Store Pattern with Signals)
  approved = computed(() => this.strategies().filter(s => s.status === 'APPROVED' || s.status === 'PENDING'));
  active = computed(() => this.strategies().filter(s => s.status === 'ACTIVE'));
  completed = computed(() => this.strategies().filter(s => s.status === 'EXPIRED' || s.status === 'REJECTED'));

  countForTab(tab: Tab): number {
    if (tab === 'GENERAZIONE') return this.generatedStrategies().length;
    if (tab === 'APPROVATE') return this.approved().length;
    if (tab === 'ATTIVE') return this.active().length;
    if (tab === 'COMPLETATE') return this.completed().length;
    return 0;
  }

  ngOnInit(): void {
    this.loadStrategies();
  }

  loadStrategies() {
    this.strategyService.getStrategies().subscribe({
      next: (data) => { this.strategies.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  onGenerate(req: StrategyRequest) {
    this.pipelineService.generateStrategies(req).subscribe(res => {
      this.generationId.set(res.generation_id);
      this.generationStatus.set('running');
      this.pollStatus(res.generation_id);
    });
  }

  pollStatus(id: string) {
    this.pipelineService.pollGenerationStatus(id).subscribe({
      next: (status: GenerationStatus) => {
        console.log('Poll status update (raw):', status);
        this.generationStatus.set(status.status);
        if (status.status === 'completed' && status.results) {
          // Assicuriamoci che i campi del profitto siano mappati correttamente
          const mappedResults = status.results.map(s => {
            const mapped = {
              ...s,
              estimated_profit_pct: Number(s.estimated_profit_pct) || 0,
              estimated_profit_eur: Number(s.estimated_profit_eur) || 0,
              budget_eur: Number(s.budget_eur) || 100
            };
            return mapped;
          });
          console.log('Poll status update (mapped):', mappedResults);
          this.generatedStrategies.set(mappedResults);
        }
      },
      error: (err) => {
        console.error('Polling error:', err);
        this.generationStatus.set('failed');
      }
    });
  }

  resetGeneration() {
    this.generationId.set(null);
    this.generationStatus.set('pending');
    this.generatedStrategies.set([]);
  }

  saveAndApprove(s: Strategy): void {
    const dto: StrategyCreateDto = {
      template: s.template,
      pair: s.pair,
      timeframe: s.timeframe,
      params: s.params,
      budget_eur: s.budget_eur,
      title: s.title,
      description: s.description
    };

    this.strategyService.createStrategy(dto).pipe(
      switchMap(newStrategy => {
        console.log('Strategia creata con successo:', newStrategy);
        if (!newStrategy.id) throw new Error('Strategy ID is missing after creation');
        return this.strategyService.approve(newStrategy.id);
      })
    ).subscribe({
      next: () => {
        console.log('Strategia approvata con successo');
        this.resetGeneration(); // Pulisce i risultati generati dopo l'approvazione
        this.loadStrategies();
        this.activeTab.set('APPROVATE');
      },
      error: (err) => console.error('Errore durante salvataggio/approvazione:', err)
    });
  }

  removeGenerated(s: Strategy) {
    this.generatedStrategies.update(list => list.filter(x => x !== s));
  }

  startStrategy(s: Strategy) {
    if (!s.id) return;
    this.strategyService.activate(s.id).subscribe(() => {
      this.loadStrategies();
      this.activeTab.set('ATTIVE');
    });
  }

  goToDetail(_s: Strategy) {
    this.router.navigate(['/active-trade']);
  }

  stopStrategy(s: Strategy) {
    this.pendingStop.set(s);
  }

  doStop(): void {
    const s = this.pendingStop();
    if (!s || !s.id) return;
    this.strategyService.reject(s.id).subscribe(() => {
      this.loadStrategies();
      this.pendingStop.set(null);
    });
  }

  approve(s: Strategy): void {
    if (!s.id) return;
    this.strategyService.approve(s.id).subscribe(() => {
      this.loadStrategies();
    });
  }

  confirmReject(s: Strategy): void {
    this.pendingReject.set(s);
  }

  doReject(): void {
    const s = this.pendingReject();
    if (!s || !s.id) return;
    this.strategyService.reject(s.id).subscribe(() => {
      this.loadStrategies();
      this.pendingReject.set(null);
    });
  }

  formatParamLabel(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatParamValue(key: string, value: unknown): string {
    if (typeof value === 'number') {
      return ' ' + value.toString();
    }
    return ' ' + String(value);
  }

  toggleExpand(id: string) {
    this.expandedStrategy.update(current => current === id ? null : id);
  }

}
