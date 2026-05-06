import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { StrategyService } from '../../core/services/strategy.service';
import { PipelineService } from '../../core/services/pipeline.service';
import { Strategy, StrategyStatus, StrategyRequest, GenerationStatus, GenerationProgressStatus, StrategyCreateDto } from '../../core/models/strategy.model';
import { BadgeStatusComponent } from '../../shared/components/badge-status/badge-status.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { StrategyRequestFormComponent } from '../../shared/components/strategy-request-form/strategy-request-form.component';
import { GenerationProgressComponent } from '../../shared/components/generation-progress/generation-progress.component';
import { NgClass, KeyValuePipe, DecimalPipe } from '@angular/common';
import { switchMap } from 'rxjs';

type Tab = 'ALL' | 'ACTIVE' | 'PENDING' | 'GENERATE';

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
    DecimalPipe
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="strategies">
      <div class="header-actions">
        <div class="tabs">
          @for (tab of tabs; track tab) {
            <button class="tab" [ngClass]="{ 'tab--active': activeTab() === tab }" (click)="activeTab.set(tab)">
              {{ tab }}
            </button>
          }
        </div>
      </div>

      @if (activeTab() === 'GENERATE') {
        <div class="generation-container">
          @if (!generationId()) {
            <app-strategy-request-form (requestSubmitted)="onGenerate($event)" />
          } @else {
            <app-generation-progress [status]="generationStatus()" />
            
            @if (generationStatus() === 'completed') {
              <div class="generated-results">
                <h3>Strategie Generate</h3>
                <div class="strategy-list">
                  @for (s of generatedStrategies(); track s.template + s.pair + $index) {
                    <div class="strategy-row strategy-row--generated">
                      <div class="strategy-info">
                        <div class="strategy-header">
                          <span class="strategy-title">{{ s.title }}</span>
                          <span class="ai-badge">AI Score: {{ s.ai_score | number:'1.0-0' }}%</span>
                        </div>
                        <p class="strategy-desc">{{ s.description }}</p>
                        <div class="strategy-meta">
                          <span class="tag">{{ s.pair }}</span>
                          <span class="tag">{{ s.timeframe }}</span>
                          @for (param of s.params | keyvalue; track param.key) {
                            <span class="tag tag--param">{{ param.key }}: {{ param.value }}</span>
                          }
                        </div>
                      </div>
                      <div class="strategy-actions">
                        <button class="btn-approve" (click)="saveAndApprove(s)">Salva e Approva</button>
                      </div>
                    </div>
                  }
                </div>
                <button class="btn-ghost mt-16" (click)="resetGeneration()">Nuova Generazione</button>
              </div>
            }
          }
        </div>
      } @else {
        @if (filtered().length === 0 && !loading()) {
          <app-empty-state message="Nessuna strategia trovata" />
        } @else {
          <div class="strategy-list">
            @for (s of filtered(); track s.id) {
              <div class="strategy-row">
                <div class="strategy-info">
                  <span class="strategy-title">{{ s.title }}</span>
                  <span class="strategy-pair">{{ s.pair }} · {{ s.timeframe }}</span>
                </div>
                <app-badge-status [status]="s.status" />
                <div class="strategy-actions">
                  @if (s.status === 'PENDING') {
                    <button class="btn-approve" (click)="approve(s)">Approva</button>
                  }
                  <button class="btn-reject" (click)="confirmReject(s)">Rifiuta</button>
                </div>
              </div>
            }
          </div>
        }
      }

      <app-confirm-dialog
        [visible]="!!pendingReject()"
        message="Rifiutare questa strategia?"
        (confirmed)="doReject()"
        (cancelled)="pendingReject.set(null)"
      />
    </div>
  `,
  styles: [`
    .header-actions { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
    .tabs { display: flex; gap: 8px; }
    .tab { background: none; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; }
    .tab--active { border-color: var(--accent-primary); color: var(--accent-primary); }
    .strategy-list { display: flex; flex-direction: column; gap: 8px; }
    .strategy-row { display: flex; align-items: center; gap: 16px; padding: 12px 16px; background: var(--bg-surface); border-radius: 8px; border: 1px solid var(--border-default); }
    .strategy-info { flex: 1; }
    .strategy-title { display: block; font-size: 14px; color: var(--text-primary); }
    .strategy-pair { font-size: 12px; color: var(--text-secondary); font-family: monospace; }
    .strategy-actions { display: flex; gap: 8px; }
    .btn-approve { background: rgba(14,203,129,0.1); color: var(--color-buy); border: 1px solid var(--color-buy); padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
    .btn-reject  { background: rgba(246,70,93,0.1);  color: var(--color-sell); border: 1px solid var(--color-sell); padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
    .btn-ghost { background:transparent; color:var(--text-secondary); border:1px solid var(--border-default); padding:8px 16px; border-radius:4px; cursor:pointer; }
    .generation-container { max-width: 800px; margin: 0 auto; }
    .generated-results { margin-top: 24px; }
    .mt-16 { margin-top: 16px; }

    /* Nuovi stili per varianti generate */
    .strategy-row--generated { flex-direction: column; align-items: stretch; gap: 12px; }
    .strategy-header { display: flex; justify-content: space-between; align-items: center; }
    .ai-badge { background: rgba(240,185,11,0.1); color: #F0B90B; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; border: 1px solid rgba(240,185,11,0.3); }
    .strategy-desc { font-size: 13px; color: var(--text-secondary); margin: 4px 0; line-height: 1.4; }
    .strategy-meta { display: flex; flex-wrap: wrap; gap: 6px; }
    .tag { background: var(--bg-card); border: 1px solid var(--border-default); padding: 2px 6px; border-radius: 4px; font-size: 11px; color: var(--text-primary); font-family: monospace; }
    .tag--param { border-color: var(--accent-primary); color: var(--accent-primary); }
  `]
})
export class StrategiesPage implements OnInit {
  private strategyService = inject(StrategyService);
  private pipelineService = inject(PipelineService);

  readonly tabs: Tab[] = ['ALL', 'ACTIVE', 'PENDING', 'GENERATE'];
  strategies = signal<Strategy[]>([]);
  activeTab = signal<Tab>('ALL');
  loading = signal(true);
  pendingReject = signal<Strategy | null>(null);

  // Generation state
  generationId = signal<string | null>(null);
  generationStatus = signal<GenerationProgressStatus>('pending');
  generatedStrategies = signal<Strategy[]>([]);

  filtered = computed(() => {
    const tab = this.activeTab();
    const all = this.strategies();
    if (tab === 'ALL') return all;
    if (tab === 'GENERATE') return [];
    return all.filter(s => s.status === (tab as StrategyStatus));
  });

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
        this.generationStatus.set(status.status);
        if (status.status === 'completed' && status.results) {
          this.generatedStrategies.set(status.results);
        }
      },
      error: () => this.generationStatus.set('failed')
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
      params: s.params
    };

    this.strategyService.createStrategy(dto).pipe(
      switchMap(newStrategy => this.strategyService.approve(newStrategy.id))
    ).subscribe(() => {
      this.loadStrategies();
      this.activeTab.set('ACTIVE');
    });
  }

  approve(s: Strategy): void {
    this.strategyService.approve(s.id).subscribe(() => {
      this.loadStrategies();
    });
  }

  confirmReject(s: Strategy): void {
    this.pendingReject.set(s);
  }

  doReject(): void {
    const s = this.pendingReject();
    if (!s) return;
    this.strategyService.reject(s.id).subscribe(() => {
      this.loadStrategies();
      this.pendingReject.set(null);
    });
  }
}
