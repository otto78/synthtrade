import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { LLMModelsService } from '../../core/services/llm-models.service';
import { LLMModelsPayload } from '../../core/models/llm-models.model';
import { Subscription } from 'rxjs';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
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
          [value]="balanceFormatted()"
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
          label="Sessione Scalping"
          [value]="sessionStr()"
          [loading]="loading()"
        />
      </div>

      @if (error()) {
        <div class="error-msg">{{ error() }}</div>
      }

      <!-- Asset Breakdown - Accordion -->
      @if (sortedAssets().length > 0 && !loading()) {
        <div class="assets-section">
          <button class="accordion-header" (click)="toggleAssets()">
            <h3>Portfolio Asset ({{ stats().currency }})</h3>
            <span class="accordion-arrow" [class.open]="assetsOpen()">▾</span>
          </button>
          @if (assetsOpen()) {
            <div class="accordion-body">
              <div class="assets-table">
                <div class="asset-row header">
                  <span class="col-asset">Asset</span>
                  <span class="col-qty">Quantità</span>
                  <span class="col-eur">Valore {{ stats().currency }}</span>
                  <span class="col-pct">% Portfolio</span>
                </div>
                @for (a of sortedAssets(); track a.asset) {
                  <div class="asset-row">
                    <span class="col-asset">{{ a.asset }}</span>
                    <span class="col-qty">{{ a.quantity | number:'1.4-8' }}</span>
                    <span class="col-eur">{{ a.value_eur | currency:stats().currency:'symbol':'1.2-2' }}</span>
                    <span class="col-pct">{{ (a.value_eur / stats().balance_eur * 100) | number:'1.1-1' }}%</span>
                  </div>
                }
              </div>
            </div>
          }
        </div>
      }

      <!-- LLM Models Configuration -->
      <!-- (hidden for now) -->
    </div>
  `,
  styles: [`
    .dashboard { padding: 24px; max-width: 1200px; margin: 0 auto; }
    .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

    .error-msg {
      margin-top: 16px; padding: 12px 16px;
      background: rgba(246,70,93,0.1); border: 1px solid rgba(246,70,93,0.3);
      border-radius: 8px; color: var(--color-sell, #F6465D);
      font-size: 13px;
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
  `]
})
export class DashboardPage implements OnInit, OnDestroy {
  private dashboardService = inject(DashboardService);
  private sub = new Subscription();

  stats = signal<DashboardStats>({
    balance_eur: 0,
    currency: 'EUR',
    balance_breakdown: {} as BalanceBreakdown,
    balance_assets: [],
    engine_status: '—',
  });
  loading = signal(true);
  error = signal<string | null>(null);
  assetsOpen = signal(false);

  sortedAssets = computed(() => {
    const assets = this.stats().balance_assets;
    if (!assets) return [];
    return [...assets].sort((a, b) => b.value_eur - a.value_eur);
  });

  balanceFormatted = computed(() => {
    const b = this.stats().balance_eur;
    const ccy = this.stats().currency || 'EUR';
    if (b === 0 && !this.loading()) return '—';
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: ccy, minimumFractionDigits: 2 }).format(b);
  });

  balanceLabel = computed(() => {
    const provider = this.stats().exchange_provider?.toUpperCase();
    if (provider === 'OKX') return 'Saldo OKX';
    if (provider === 'BINANCE') return 'Saldo Binance';
    return 'Saldo Exchange';
  });

  activeStrategiesStr = computed(() => String(this.stats().active_strategies_count ?? 0));
  openTradesStr = computed(() => String(this.stats().open_trades_count ?? 0));
  sessionStr = computed(() => {
    const count = this.stats().active_session_count ?? 0;
    return count > 0 ? 'Attiva' : '0';
  });

  ngOnInit(): void {
    this.loadStats();
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }

  toggleAssets(): void {
    this.assetsOpen.update(v => !v);
  }

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
}