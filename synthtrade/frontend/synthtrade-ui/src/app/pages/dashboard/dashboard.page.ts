import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType } from '../../core/models/ws-message.model';
import { DashboardStats } from '../../core/models/dashboard.model';
import { DecimalPipe } from '@angular/common';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';
import { SignedNumberPipe } from '../../shared/pipes/signed-number.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [StatCardComponent, SignedNumberPipe, DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="dashboard">
      <div class="stats-grid">
        <app-stat-card
          label="Balance"
          [value]="stats().balance | number:'1.2-2'"
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
    </div>
  `,
  styles: [`
    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;
    }
  `]
})
export class DashboardPage implements OnInit, OnDestroy {
  private dashboardService = inject(DashboardService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  stats = signal<DashboardStats>({ balance: 0, pnl_today: 0, active_strategy: null, engine_status: '—' });
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
