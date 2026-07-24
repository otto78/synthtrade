import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { LLMModelsService } from '../../core/services/llm-models.service';
import { LLMModelsPayload } from '../../core/models/llm-models.model';
import { Subscription } from 'rxjs';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { DashboardStats, BalanceBreakdown, BalanceSnapshot } from '../../core/models/dashboard.model';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [StatCardComponent, CurrencyPipe, DecimalPipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="dashboard">
      <!-- KPI Cards -->
      <div class="stats-grid">
        <app-stat-card
          [label]="balanceLabel()"
          [value]="(balanceFormatted())"
          [loading]="loading()"
        />
        <app-stat-card
          label="PnL Oggi"
          [value]="pnlTodayStr()"
          [delta]="stats().pnl_today"
          [loading]="loading()"
        />
        <app-stat-card
          label="Strategie Attive"
          [value]="activeStrategiesStr()"
          [loading]="loading()"
        />
        <app-stat-card
          label="Trade Aperti"
          [value]="openTradesStr()"
          [loading]="loading()"
        />
        <app-stat-card
          label="Trade Chiusi Oggi"
          [value]="closedTradesStr()"
          [delta]="stats().closed_trades_pnl ?? 0"
          [loading]="loading()"
        />
      </div>

      @if (error()) {
        <div class="error-msg">{{ error() }}</div>
      }

      <!-- Equity Chart -->
      <div class="chart-section">
        <div class="chart-header">
          <h3>Andamento Saldo</h3>
          <div class="chart-toggles">
            @for (r of ranges; track r) {
              <button
                class="toggle-btn"
                [class.active]="selectedRange() === r"
                (click)="loadEquity(r)"
              >
                {{ r }}
              </button>
            }
          </div>
        </div>
        <div class="chart-container">
          @if (equityData().length > 0) {
            <svg class="equity-chart" [attr.viewBox]="viewBox()">
              <!-- Grid lines -->
              @for (gl of gridLines(); track $index) {
                <line
                  [attr.x1]="gl.x1" [attr.y1]="gl.y1"
                  [attr.x2]="gl.x2" [attr.y2]="gl.y2"
                  class="grid-line"
                />
              }
              <!-- Area fill -->
              <path [attr.d]="areaPath()" class="chart-area" />
              <!-- Line -->
              <path [attr.d]="linePath()" class="chart-line" />
              <!-- Dots -->
              @for (pt of chartPoints(); track $index) {
                <circle
                  [attr.cx]="pt.x" [attr.cy]="pt.y" r="3"
                  [class.dot-positive]="pt.value >= 0"
                  [class.dot-negative]="pt.value < 0"
                />
              }
            </svg>
            <div class="chart-metrics">
              <span class="metric" [class.positive]="pnlTotal() >= 0" [class.negative]="pnlTotal() < 0">
                P&L: {{ pnlTotal() | number:'1.2-2' }} USD
              </span>
            </div>
          } @else {
            <div class="chart-empty">
              <span>Nessun dato disponibile per questo periodo</span>
            </div>
          }
        </div>
      </div>

      <!-- Asset Breakdown - Accordion -->
      @if (sortedAssets().length > 0 && !loading()) {
        <div class="assets-section">
          <button class="accordion-header" (click)="toggleAssets()">
            <h3>Portfolio Asset</h3>
            <span class="accordion-arrow" [class.open]="assetsOpen()">▾</span>
          </button>
          @if (assetsOpen()) {
            <div class="accordion-body">
              <div class="assets-table">
                <div class="asset-row header">
                  <span class="col-asset">Asset</span>
                  <span class="col-qty">Quantità</span>
                  <span class="col-eur">Valore USD</span>
                  <span class="col-pct">% Portfolio</span>
                </div>
                @for (a of sortedAssets(); track a.asset) {
                  <div class="asset-row">
                    <span class="col-asset">{{ a.asset }}</span>
                    <span class="col-qty">{{ a.quantity | number:'1.4-8' }}</span>
                    <span class="col-eur">{{ a.value_eur | currency:'USD':'symbol':'1.2-2' }}</span>
                    <span class="col-pct">{{ (a.value_eur / stats().balance_eur * 100) | number:'1.1-1' }}%</span>
                  </div>
                }
              </div>
            </div>
          }
        </div>
      }

      <!-- LLM Models Configuration -->
      <!-- <div class="llm-section">
        <button class="accordion-header" (click)="toggleLLM()">
          <h3>Modelli LLM</h3>
          <span class="accordion-arrow" [class.open]="llmOpen()">▾</span>
        </button>
        @if (llmOpen()) {
          <div class="accordion-body">
            <div class="llm-form">
              <p class="llm-hint">
                I modelli free potrebbero non essere più disponibili. Sostituisci qui i modelli della cascata.
              </p>

              @if (llmModels().cascade.length > 0) {
                @for (model of llmModels().cascade; track $index) {
                  <div class="llm-field">
                    <label class="llm-label">{{ model }}</label>
                    <input
                      class="llm-input"
                      [ngModel]="getCascade($index)"
                      (ngModelChange)="setCascade($index, $event)"
                      placeholder="Nuovo modello..."
                    />
                  </div>
                }
              } @else {
                <div class="llm-empty">Nessun modello caricato. Clicca "Carica" per recuperarli.</div>
              }

              <div class="llm-actions">
                <button class="llm-btn llm-btn-load" (click)="loadLLMModels()" [disabled]="llmLoading()">
                  {{ llmLoading() ? 'Caricamento...' : 'Carica' }}
                </button>
                <button
                  class="llm-btn llm-btn-save"
                  (click)="saveLLMModels()"
                  [disabled]="llmLoading() || llmModels().cascade.length === 0"
                >
                  {{ llmLoading() ? 'Salvataggio...' : 'Salva' }}
                </button>
              </div>

              @if (llmMessage()) {
                <div class="llm-message">{{ llmMessage() }}</div>
              }
            </div>
          </div>
        }
      </div> -->
    </div>
  `,
  styles: [`
    .dashboard { padding: 24px; max-width: 1200px; margin: 0 auto; }
    .stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }

    /* Chart Section */
    .chart-section { margin-top: 24px; }
    .chart-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 12px;
    }
    .chart-header h3 {
      font-size: 13px; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 1px; margin: 0;
    }
    .chart-toggles { display: flex; gap: 4px; background: var(--bg-surface); padding: 3px; border-radius: 6px; }
    .toggle-btn {
      background: none; border: none; color: var(--text-secondary);
      padding: 4px 12px; border-radius: 4px; cursor: pointer;
      font-size: 11px; font-weight: 600; transition: all 0.2s;
    }
    .toggle-btn.active { background: var(--bg-elevated); color: var(--accent-primary); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .toggle-btn:hover:not(.active) { color: var(--text-primary); }

    .chart-container {
      background: var(--bg-card); border: 1px solid var(--border-default);
      border-radius: 12px; padding: 20px; position: relative;
    }
    .equity-chart { width: 100%; height: 200px; overflow: visible; }
    .grid-line { stroke: rgba(255,255,255,0.04); stroke-width: 1; }
    .chart-area { fill: rgba(14,203,129,0.08); }
    .chart-line { fill: none; stroke: var(--color-buy, #0ECB81); stroke-width: 2; stroke-linejoin: round; }
    .dot-positive { fill: var(--color-buy, #0ECB81); }
    .dot-negative { fill: var(--color-sell, #F6465D); }
    .chart-metrics {
      margin-top: 8px; text-align: right;
    }
    .metric { font-size: 13px; font-weight: 600; font-family: monospace; }
    .metric.positive { color: var(--color-buy, #0ECB81); }
    .metric.negative { color: var(--color-sell, #F6465D); }
    .chart-empty {
      height: 200px; display: flex; align-items: center; justify-content: center;
      color: var(--text-muted); font-size: 13px;
    }

    /* Asset Table - Accordion */
    .assets-section { margin-top: 24px; border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; }
    .accordion-header {
      display: flex; justify-content: space-between; align-items: center;
      width: 100%; padding: 14px 16px;
      background: var(--bg-surface); border: none; cursor: pointer;
      transition: background 0.2s;
    }
    .accordion-header:hover { background: var(--bg-elevated); }
    .accordion-header h3 {
      font-size: 13px; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 1px; margin: 0;
    }
    .accordion-arrow {
      font-size: 12px; color: var(--text-secondary);
      transition: transform 0.2s ease;
    }
    .accordion-arrow.open { transform: rotate(180deg); }
    .accordion-body { border-top: 1px solid var(--border-default); }
    .assets-table { background: var(--bg-card); }
    .asset-row {
      display: grid;
      grid-template-columns: 100px 1fr 120px 100px;
      gap: 16px; padding: 10px 16px;
      font-family: monospace; font-size: 13px;
    }
    .asset-row.header {
      color: var(--text-muted); font-size: 11px;
      text-transform: uppercase; letter-spacing: 1px;
      background: rgba(255,255,255,0.03);
    }
    .asset-row:not(.header) {
      color: var(--text-primary);
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .asset-row:last-child { border-bottom: none; }
    .col-asset { font-weight: 600; }
    .col-eur, .col-pct { text-align: right; }

    /* LLM Models Configuration */
    .llm-section { margin-top: 24px; border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; }
    .llm-form {
      padding: 20px;
      background: var(--bg-card, #1A1D23);
    }
    .llm-hint {
      font-size: 12px; color: var(--text-secondary, #848E9C);
      margin: 0 0 16px 0; line-height: 1.5;
    }
    .llm-field {
      margin-bottom: 14px;
    }
    .llm-field:last-of-type {
      margin-bottom: 0;
    }
    .llm-label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      font-family: monospace;
      color: var(--text-secondary, #848E9C);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .llm-input {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid rgba(234,236,239,0.1);
      border-radius: 6px;
      background: var(--bg-surface, #0D1117);
      color: var(--text-primary, #E8EAED);
      font-size: 14px;
      font-family: monospace;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      box-sizing: border-box;
    }
    .llm-input:focus {
      border-color: var(--accent-primary, #0ECB81);
      box-shadow: 0 0 0 2px rgba(14,203,129,0.15);
    }
    .llm-input::placeholder {
      color: var(--text-muted, #5A5F6B);
    }
    .llm-empty {
      font-size: 13px; color: var(--text-muted, #5A5F6B);
      text-align: center; padding: 16px 0;
    }
    .llm-actions {
      display: flex; gap: 10px; margin-top: 18px;
    }
    .llm-btn {
      flex: 1;
      padding: 10px 16px;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .llm-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .llm-btn-load {
      background: var(--bg-surface, #0D1117);
      color: var(--text-primary, #E8EAED);
      border: 1px solid rgba(234,236,239,0.1);
    }
    .llm-btn-load:hover:not(:disabled) {
      background: var(--bg-elevated, #262A33);
    }
    .llm-btn-save {
      background: var(--accent-primary, #0ECB81);
      color: #000;
    }
    .llm-btn-save:hover:not(:disabled) {
      background: #0AB770;
    }
    .llm-message {
      margin-top: 12px;
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      background: rgba(14,203,129,0.08);
      color: var(--color-buy, #0ECB81);
      border: 1px solid rgba(14,203,129,0.2);
    }
  `]
})
export class DashboardPage implements OnInit, OnDestroy {
  private dashboardService = inject(DashboardService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  stats = signal<DashboardStats>({
    balance_eur: 0,
    balance_breakdown: {} as BalanceBreakdown,
    balance_assets: [],
    pnl_today: 0,
    engine_status: '—',
  });
  loading = signal(true);
  error = signal<string | null>(null);
  equityData = signal<BalanceSnapshot[]>([]);
  selectedRange = signal('1m');
  ranges = ['1d', '1w', '1m', '1y'];
  assetsOpen = signal(false);

  sortedAssets = computed(() => {
    const assets = this.stats().balance_assets;
    if (!assets) return [];
    return [...assets].sort((a, b) => b.value_eur - a.value_eur);
  });

  balanceFormatted = computed(() => {
    const b = this.stats().balance_eur;
    if (b === 0 && !this.loading()) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(b);
  });

  balanceLabel = computed(() => {
    const provider = this.stats().exchange_provider?.toUpperCase();
    if (provider === 'OKX') return 'Saldo OKX';
    if (provider === 'BINANCE') return 'Saldo Binance';
    return 'Saldo Exchange';
  });

  activeStrategiesStr = computed(() => String(this.stats().active_strategies_count ?? 0));
  openTradesStr = computed(() => String(this.stats().open_trades_count ?? 0));
  closedTradesStr = computed(() => {
    const count = this.stats().closed_trades_count ?? 0;
    const pnl = this.stats().closed_trades_pnl ?? 0;
    return `${count} (${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} USD)`;
  });
  pnlTodayStr = computed(() => {
    const pnl = this.stats().pnl_today;
    if (pnl === 0) return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', signDisplay: 'always', minimumFractionDigits: 2 }).format(pnl);
  });

  llmOpen = signal(false);

  toggleAssets(): void {
    this.assetsOpen.update(v => !v);
  }

  toggleLLM(): void {
    this.llmOpen.update(v => !v);
  }

  // Chart computations
  chartPoints = computed(() => {
    const data = this.equityData();
    if (data.length < 2) return [];

    const values = data.map(d => d.value);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 1);
    const range = max - min || 1;
    const w = 1000;
    const h = 180;
    const stepX = w / (data.length - 1);

    return data.map((d, i) => ({
      x: i * stepX,
      y: h - ((d.value - min) / range) * h,
      value: d.value,
    }));
  });

  viewBox = computed(() => {
    return `0 0 1000 200`;
  });

  linePath = computed(() => {
    const pts = this.chartPoints();
    if (pts.length < 2) return '';
    return pts.map((p, idx) => `${idx === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  });

  areaPath = computed(() => {
    const pts = this.chartPoints();
    if (pts.length < 2) return '';
    const bottom = 180;
    const top = pts[0];
    const bottomRight = pts[pts.length - 1];
    return `M${top.x},${bottom} L${top.x},${top.y} ${pts.slice(1).map((p) => `L${p.x},${p.y}`).join(' ')} L${bottomRight.x},${bottom} Z`;
  });

  gridLines = computed<{x1: number; y1: number; x2: number; y2: number}[]>(() => {
    const h = 180;
    return [25, 50, 75].map(pct => ({
      x1: 0, y1: h * pct / 100,
      x2: 1000, y2: h * pct / 100,
    }));
  });

  pnlTotal = computed(() => {
    const data = this.equityData();
    if (data.length < 2) return 0;
    return Math.round((data[data.length - 1].value - data[0].value) * 100) / 100;
  });

  ngOnInit(): void {
    this.loadStats();
    this.loadEquity('1m');
  }

  // ---------- LLM model management ----------
  private llmService = inject(LLMModelsService);
  readonly llmModels = signal<LLMModelsPayload>({ cascade: [], fallback: '' });
  readonly newCascade = signal<string[]>([]);
  readonly llmLoading = signal(false);
  readonly llmMessage = signal('');

  async loadLLMModels() {
    this.llmLoading.set(true);
    try {
      const data = await firstValueFrom(this.llmService.getModels());
      this.llmModels.set(data);
      // initialise editable fields with current values
      this.newCascade.set([...data.cascade]);
    } catch (e) {
      this.llmMessage.set('Errore nel caricamento dei modelli');
    } finally {
      this.llmLoading.set(false);
    }
  }

  async saveLLMModels() {
    this.llmLoading.set(true);
    this.llmMessage.set('');
    try {
      const payload = {
        cascade: this.newCascade().map(v => v.trim()).filter(Boolean),
        fallback: this.llmModels().fallback,
      } as LLMModelsPayload;
      await firstValueFrom(this.llmService.setModels(payload));
      this.llmModels.set(payload);
      this.llmMessage.set('Modelli salvati');
    } catch (e) {
      this.llmMessage.set('Errore nel salvataggio');
    } finally {
      this.llmLoading.set(false);
    }
  }

  // Helper getters/setters for the cascade inputs (required for ngModel binding)
  getCascade(index: number): string {
    const arr = this.newCascade();
    return arr[index] ?? '';
  }
  setCascade(index: number, value: string): void {
    const arr = [...this.newCascade()];
    arr[index] = value;
    this.newCascade.set(arr);
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }

  loadStats(): void {
    this.sub.add(
      this.dashboardService.getStats().subscribe({
        next: (data) => {
          this.stats.set(data);
          this.loading.set(false);
          this.error.set(null);
        },
        error: (err) => {
          this.loading.set(false);
          this.error.set('Failed to load dashboard stats');
          console.error('Dashboard stats error:', err);
        },
      })
    );
  }

  loadEquity(range: string): void {
    this.selectedRange.set(range);
    this.sub.add(
      this.dashboardService.getEquityHistory(range).subscribe({
        next: (data) => this.equityData.set(data),
        error: (err) => console.error('Equity history error:', err),
      })
    );
  }
}