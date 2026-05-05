import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { Subscription } from 'rxjs';
import { DashboardService } from '../../core/services/dashboard.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType, WsPricePayload } from '../../core/models/ws-message.model';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { PriceTickerComponent } from '../../shared/components/price-ticker/price-ticker.component';
import { SignedNumberPipe } from '../../shared/pipes/signed-number.pipe';

@Component({
  selector: 'app-active-trade',
  standalone: true,
  imports: [NgClass, EmptyStateComponent, PriceTickerComponent, SignedNumberPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (!activeStrategy()) {
      <app-empty-state message="Nessun trade attivo" icon="📊" />
    } @else {
      <div class="active-trade">
        <div class="trade-header">
          <span class="trade-title">{{ activeStrategy()!.title }}</span>
          <span class="trade-pair">{{ activeStrategy()!.pair }}</span>
        </div>

        <div class="trade-kpis">
          <div class="kpi">
            <span class="kpi-label">Prezzo</span>
            @if (currentPrice() > 0) {
              <app-price-ticker [price]="currentPrice()" />
            } @else {
              <span class="kpi-value">—</span>
            }
          </div>
          <div class="kpi">
            <span class="kpi-label">P&L</span>
            <span class="pnl kpi-value" [ngClass]="{ positive: pnl() > 0, negative: pnl() < 0 }">
              {{ pnl() | signedNumber }}%
            </span>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .active-trade { padding: 8px; }
    .trade-header { margin-bottom: 24px; }
    .trade-title { display: block; font-size: 20px; color: var(--text-primary); font-family: 'Chakra Petch', sans-serif; }
    .trade-pair { font-size: 13px; color: var(--text-secondary); font-family: monospace; }
    .trade-kpis { display: flex; gap: 24px; }
    .kpi { display: flex; flex-direction: column; gap: 4px; }
    .kpi-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 20px; font-family: monospace; color: var(--text-primary); }
    .positive { color: var(--color-buy, #0ECB81); }
    .negative { color: var(--color-sell, #F6465D); }
  `]
})
export class ActiveTradePage implements OnInit, OnDestroy {
  private dashboardService = inject(DashboardService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  activeStrategy = signal<{ id?: string; title?: string; pair?: string } | null>(null);
  currentPrice = signal(0);
  pnl = signal(0);

  ngOnInit(): void {
    this.sub.add(
      this.dashboardService.getStats().subscribe(data => {
        this.activeStrategy.set(data.active_strategy);
      })
    );
    this.sub.add(
      this.wsService.on<WsPricePayload>(WsMessageType.Price).subscribe(msg => {
        if (msg.payload) this.currentPrice.set(msg.payload.price);
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}
