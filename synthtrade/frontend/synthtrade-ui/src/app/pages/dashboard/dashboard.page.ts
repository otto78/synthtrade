import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { Router } from '@angular/router';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType } from '../../core/models/ws-message.model';
import { DashboardStats, BalanceBreakdown } from '../../core/models/dashboard.model';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';
import { SignedNumberPipe } from '../../shared/pipes/signed-number.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [StatCardComponent, SignedNumberPipe, CurrencyPipe, DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="dashboard">
      <!-- KPI Cards -->
      <div class="stats-grid">
        <app-stat-card
          label="Saldo Binance"
          [value]="(stats().balance_eur | currency:'EUR':'symbol':'1.2-2') ?? '—'"
          [loading]="loading()"
        />
        <app-stat-card
          label="PnL Oggi"
          [value]="stats().pnl_today | signedNumber"
          [delta]="stats().pnl_today"
          [loading]="loading()"
        />
        <app-stat-card
          label="Engine"
          [value]="stats().engine_status"
          [loading]="loading()"
        />
      </div>

      <!-- Active Strategy Card (TASK-328) -->
      @if (stats().active_strategy; as strategy) {
        <div class="strategy-card" (click)="goToMonitor()">
          <div class="sc-header">
            <div class="sc-info">
              <span class="sc-title">{{ strategy.title }}</span>
              <span class="sc-meta">{{ strategy.pair }} · {{ strategy.timeframe }}</span>
            </div>
            <div class="sc-status">
              <span class="pulse-dot"></span>
              Attiva
            </div>
          </div>
          <div class="sc-stats">
            <div class="sc-stat">
              <span class="sc-stat-label">Score</span>
              <span class="sc-stat-value">{{ strategy.score ?? '—' }}</span>
            </div>
            <div class="sc-stat">
              <span class="sc-stat-label">Budget</span>
              <span class="sc-stat-value">{{ strategy.budget_eur | currency:'EUR':'symbol':'1.0-0' }}</span>
            </div>
            <div class="sc-stat">
              <span class="sc-stat-label">Rischio AI</span>
              <span class="sc-stat-value" [class]="'risk-' + (strategy.ai_risk?.toLowerCase() || 'medium')">
                {{ strategy.ai_risk || '—' }}
              </span>
            </div>
          </div>
          <div class="sc-footer">
            <button class="btn-monitor">📊 Monitora</button>
          </div>
        </div>
      }

      <!-- Asset Breakdown (ordinato per valore EUR decrescente - TASK-327) -->
      @if (sortedAssets().length > 0 && !loading()) {
        <div class="assets-section">
          <h3>Portfolio Asset</h3>
          <div class="assets-table">
            <div class="asset-row header">
              <span class="col-asset">Asset</span>
              <span class="col-qty">Quantità</span>
              <span class="col-eur">Valore EUR</span>
              <span class="col-pct">% Portfolio</span>
            </div>
            @for (a of sortedAssets(); track a.asset) {
              <div class="asset-row">
                <span class="col-asset">{{ a.asset }}</span>
                <span class="col-qty">{{ a.quantity | number:'1.4-8' }}</span>
                <span class="col-eur">{{ a.value_eur | currency:'EUR':'symbol':'1.2-2' }}</span>
                <span class="col-pct">{{ (a.value_eur / stats().balance_eur * 100) | number:'1.1-1' }}%</span>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;
    }

    /* Active Strategy Card */
    .strategy-card {
      margin-top: 24px;
      background: var(--bg-card);
      border: 1px solid var(--border-default);
      border-radius: 12px;
      padding: 20px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .strategy-card:hover { border-color: var(--accent-primary); transform: translateY(-2px); }
    .sc-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
    .sc-info { display: flex; flex-direction: column; gap: 4px; }
    .sc-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
    .sc-meta { font-size: 13px; color: var(--text-secondary); font-family: monospace; }
    .sc-status { display: flex; align-items: center; gap: 8px; color: var(--color-buy); font-size: 12px; font-weight: 700; }
    .pulse-dot { width: 8px; height: 8px; background: var(--color-buy); border-radius: 50%; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    .sc-stats { display: flex; gap: 24px; margin-bottom: 16px; }
    .sc-stat { display: flex; flex-direction: column; gap: 2px; }
    .sc-stat-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; }
    .sc-stat-value { font-size: 16px; font-weight: 700; font-family: monospace; }
    .risk-low { color: var(--color-buy); }
    .risk-medium { color: var(--accent-primary); }
    .risk-high { color: var(--color-sell); }
    .sc-footer { border-top: 1px solid var(--border-default); padding-top: 12px; }
    .btn-monitor {
      background: transparent; border: 1px solid var(--border-default);
      color: var(--text-secondary); padding: 8px 20px; border-radius: 6px;
      cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s;
    }
    .btn-monitor:hover { border-color: var(--accent-primary); color: var(--accent-primary); }

    /* Asset Table */
    .assets-section { margin-top: 24px; }
    .assets-section h3 {
      font-size: 13px; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;
    }
    .assets-table { background: var(--surface); border-radius: 8px; overflow: hidden; }
    .asset-row {
      display: grid;
      grid-template-columns: 100px 1fr 120px 100px;
      gap: 16px; padding: 10px 16px;
      font-family: monospace; font-size: 13px;
    }
    .asset-row.header {
      color: var(--text-muted); font-size: 11px;
      text-transform: uppercase; letter-spacing: 1px;
      background: var(--surface-hover, rgba(255,255,255,0.04));
    }
    .asset-row:not(.header) {
      color: var(--text-primary);
      border-bottom: 1px solid var(--border, rgba(255,255,255,0.06));
    }
    .asset-row:last-child { border-bottom: none; }
    .col-asset { font-weight: 600; }
    .col-eur, .col-pct { text-align: right; }
  `]
})
export class DashboardPage implements OnInit, OnDestroy {
  private dashboardService = inject(DashboardService);
  private wsService = inject(WsService);
  private router = inject(Router);
  private sub = new Subscription();

  stats = signal<DashboardStats>({
    balance_eur: 0,
    balance_breakdown: {} as BalanceBreakdown,
    balance_assets: [],
    pnl_today: 0,
    active_strategy: null,
    engine_status: '—',
  });
  loading = signal(true);

  sortedAssets = computed(() => {
    const assets = this.stats().balance_assets;
    if (!assets) return [];
    return [...assets].sort((a, b) => b.value_eur - a.value_eur);
  });

  ngOnInit(): void {
    this.sub.add(
      this.dashboardService.getStats().subscribe({
        next: (data) => { this.stats.set(data); this.loading.set(false); },
        error: () => this.loading.set(false),
      })
    );
    this.sub.add(
      this.wsService.on<Partial<DashboardStats>>(WsMessageType.StatsUpdate).subscribe(msg => {
        if (msg.payload) this.stats.update(s => ({ ...s, ...msg.payload! }));
      })
    );
  }

  goToMonitor() {
    const s = this.stats().active_strategy;
    if (s?.id) this.router.navigate(['/active-trade']);
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}
