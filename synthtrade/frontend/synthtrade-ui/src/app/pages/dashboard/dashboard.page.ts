import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { CurrencyPipe, DecimalPipe, NgClass } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType } from '../../core/models/ws-message.model';
import { DashboardStats, BalanceAsset, BalanceBreakdown } from '../../core/models/dashboard.model';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';
import { SignedNumberPipe } from '../../shared/pipes/signed-number.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [StatCardComponent, SignedNumberPipe, CurrencyPipe, DecimalPipe, NgClass],
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
          label="Strategia Attiva"
          [value]="stats().active_strategy?.title ?? '—'"
          [loading]="loading()"
        />
        <app-stat-card
          label="Engine"
          [value]="stats().engine_status"
          [loading]="loading()"
        />
      </div>

      <!-- Asset Breakdown -->
      @if (stats().balance_assets && stats().balance_assets.length > 0 && !loading()) {
        <div class="assets-section">
          <h3>Portfolio Asset</h3>
          <div class="assets-table">
            <div class="asset-row header">
              <span class="col-asset">Asset</span>
              <span class="col-qty">Quantità</span>
              <span class="col-eur">Valore EUR</span>
            </div>
            @for (a of stats().balance_assets; track a.asset) {
              <div class="asset-row">
                <span class="col-asset">{{ a.asset }}</span>
                <span class="col-qty">{{ a.quantity | number:'1.4-8' }}</span>
                <span class="col-eur">{{ a.value_eur | currency:'EUR':'symbol':'1.2-2' }}</span>
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
    .assets-section {
      margin-top: 24px;
    }
    .assets-section h3 {
      font-size: 13px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 12px;
    }
    .assets-table {
      background: var(--surface);
      border-radius: 8px;
      overflow: hidden;
    }
    .asset-row {
      display: grid;
      grid-template-columns: 100px 1fr 120px;
      gap: 16px;
      padding: 10px 16px;
      font-family: monospace;
      font-size: 13px;
    }
    .asset-row.header {
      color: var(--text-muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      background: var(--surface-hover, rgba(255,255,255,0.04));
    }
    .asset-row:not(.header) {
      color: var(--text-primary);
      border-bottom: 1px solid var(--border, rgba(255,255,255,0.06));
    }
    .asset-row:last-child { border-bottom: none; }
    .col-asset { font-weight: 600; }
    .col-eur { text-align: right; }
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
    active_strategy: null,
    engine_status: '—',
  });
  loading = signal(true);

  ngOnInit(): void {
    this.sub.add(
      this.dashboardService.getStats().subscribe({
        next: (data) => { this.stats.set(data); this.loading.set(false); },
        error: () => this.loading.set(false),
      })
    );
    this.sub.add(
      this.wsService.on<Partial<DashboardStats>>(WsMessageType.StatsUpdate).subscribe(msg => {
        if (msg.payload) this.stats.update(s => ({ ...s, ...msg.payload }));
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}
