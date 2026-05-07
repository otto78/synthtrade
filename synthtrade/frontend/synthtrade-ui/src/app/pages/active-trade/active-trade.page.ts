import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Strategy } from '../../core/models/strategy.model';
import { NgClass, DatePipe } from '@angular/common';
import { Subscription, interval, startWith, switchMap } from 'rxjs';
import { DashboardService } from '../../core/services/dashboard.service';
import { StrategyService } from '../../core/services/strategy.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType, WsPricePayload } from '../../core/models/ws-message.model';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { PriceTickerComponent } from '../../shared/components/price-ticker/price-ticker.component';
import { SignedNumberPipe } from '../../shared/pipes/signed-number.pipe';

interface MonitorData {
  stats?: {
    total_pnl_pct: number;
    win_rate: number;
    active_trades: number;
    equity_curve: number[];
  };
  recent_trades?: {
    id: string;
    executed_at: string;
    symbol: string;
    side: string;
    pnl_pct: number;
    status: string;
  }[];
}

@Component({
  selector: 'app-active-trade',
  standalone: true,
  imports: [NgClass, EmptyStateComponent, PriceTickerComponent, SignedNumberPipe, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (!activeStrategy()) {
      <app-empty-state message="Nessun trade attivo" icon="📊" />
    } @else {
      <div class="active-trade">
        <!-- Header con Stato e Titolo -->
        <div class="trade-header">
          <div class="title-row">
            <span class="trade-title">{{ activeStrategy()?.title }}</span>
            <div class="status-indicator">
              <span class="pulse-dot"></span>
              MONITORAGGIO ATTIVO
            </div>
          </div>
          <span class="trade-pair">{{ activeStrategy()?.pair }} · {{ activeStrategy()?.timeframe }}</span>
        </div>

        <!-- KPIs Principali -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <span class="kpi-label">Prezzo Attuale</span>
            <div class="kpi-main">
              @if (currentPrice() > 0) {
                <app-price-ticker [price]="currentPrice()" />
              } @else {
                <span class="loading-placeholder">...</span>
              }
            </div>
          </div>
          
          <div class="kpi-card">
            <span class="kpi-label">P&L Totale</span>
            <div class="kpi-main" [ngClass]="{ positive: (monitorData()?.stats?.total_pnl_pct ?? 0) > 0, negative: (monitorData()?.stats?.total_pnl_pct ?? 0) < 0 }">
              {{ monitorData()?.stats?.total_pnl_pct || 0 | signedNumber }}%
            </div>
          </div>

          <div class="kpi-card">
            <span class="kpi-label">Win Rate</span>
            <div class="kpi-main highlight">
              {{ monitorData()?.stats?.win_rate || 0 }}%
            </div>
          </div>

          <div class="kpi-card">
            <span class="kpi-label">Trade Aperti</span>
            <div class="kpi-main highlight">
              {{ monitorData()?.stats?.active_trades || 0 }}
            </div>
          </div>
        </div>

        <!-- Sezione Grafico (Placeholder per ora) -->
        <div class="chart-section">
          <div class="section-header">
            <h3>Equity Curve (Performance Storica)</h3>
          </div>
          <div class="equity-viz">
            @if ((monitorData()?.stats?.equity_curve?.length ?? 0) > 0) {
              <div class="curve-points">
                @for (point of monitorData()?.stats?.equity_curve; track $index) {
                  <div class="point-bar" [style.height.%]="point" [title]="point + '%'"></div>
                }
              </div>
            } @else {
              <div class="empty-chart">Dati storici insufficienti per il grafico</div>
            }
          </div>
        </div>

        <!-- Lista Trade Recenti -->
        <div class="trades-section">
          <div class="section-header">
            <h3>Operazioni Recenti</h3>
          </div>
          <div class="trades-table">
            <div class="table-header">
              <span>Data</span>
              <span>Asset</span>
              <span>Direzione</span>
              <span>P&L</span>
              <span>Stato</span>
            </div>
            @for (trade of monitorData()?.recent_trades; track trade.id) {
              <div class="table-row">
                <span class="cell-date">{{ trade.executed_at | date:'dd/MM HH:mm' }}</span>
                <span class="cell-asset">{{ trade.symbol }}</span>
                <span class="cell-side" [ngClass]="trade.side.toLowerCase()">{{ trade.side }}</span>
                <span class="cell-pnl" [ngClass]="{ positive: trade.pnl_pct > 0, negative: trade.pnl_pct < 0 }">
                  {{ trade.pnl_pct | signedNumber }}%
                </span>
                <span class="cell-status">
                  <span class="status-dot" [ngClass]="trade.status.toLowerCase()"></span>
                  {{ trade.status }}
                </span>
              </div>
            } @empty {
              <div class="empty-table">In attesa del primo segnale operativo...</div>
            }
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .active-trade { padding: 24px; max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; }
    
    .trade-header { border-bottom: 1px solid var(--border-default); padding-bottom: 16px; }
    .title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .trade-title { font-size: 24px; font-weight: 700; color: var(--text-primary); }
    .trade-pair { font-size: 14px; color: var(--text-secondary); font-family: monospace; }
    
    .status-indicator { display: flex; align-items: center; gap: 8px; color: var(--color-buy); font-size: 12px; font-weight: 700; background: rgba(14,203,129,0.1); padding: 4px 12px; border-radius: 20px; }
    .pulse-dot { width: 8px; height: 8px; background: var(--color-buy); border-radius: 50%; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(14,203,129,0.4); } 70% { box-shadow: 0 0 0 10px rgba(14,203,129,0); } 100% { box-shadow: 0 0 0 0 rgba(14,203,129,0); } }

    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
    .kpi-card { background: var(--bg-card); border: 1px solid var(--border-default); padding: 20px; border-radius: 12px; }
    .kpi-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: block; }
    .kpi-main { font-size: 24px; font-weight: 700; font-family: monospace; color: var(--text-primary); }
    .kpi-main.highlight { color: var(--accent-primary); }
    .positive { color: var(--color-buy); }
    .negative { color: var(--color-sell); }

    .section-header { margin-bottom: 16px; }
    .section-header h3 { font-size: 18px; color: var(--text-primary); margin: 0; }

    .chart-section { background: var(--bg-card); border: 1px solid var(--border-default); padding: 24px; border-radius: 16px; }
    .equity-viz { height: 150px; display: flex; align-items: flex-end; gap: 4px; padding-top: 20px; border-bottom: 1px solid var(--border-default); }
    .point-bar { flex: 1; background: var(--accent-primary); opacity: 0.6; border-radius: 2px 2px 0 0; min-width: 10px; transition: height 0.3s ease; }
    .point-bar:hover { opacity: 1; }
    .empty-chart { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); font-style: italic; }

    .trades-section { background: var(--bg-card); border: 1px solid var(--border-default); padding: 24px; border-radius: 16px; }
    .trades-table { display: flex; flex-direction: column; }
    .table-header { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; padding: 12px; border-bottom: 1px solid var(--border-default); color: var(--text-secondary); font-size: 12px; font-weight: 600; }
    .table-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; padding: 16px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); align-items: center; transition: background 0.2s; }
    .table-row:hover { background: rgba(255,255,255,0.02); }
    .cell-date { color: var(--text-secondary); font-size: 13px; }
    .cell-asset { font-weight: 600; color: var(--text-primary); }
    .cell-side { font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .cell-side.buy { color: var(--color-buy); }
    .cell-side.sell { color: var(--color-sell); }
    .cell-pnl { font-family: monospace; font-weight: 700; }
    .cell-status { display: flex; align-items: center; gap: 6px; font-size: 12px; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; }
    .status-dot.open { background: var(--color-buy); box-shadow: 0 0 8px var(--color-buy); }
    .status-dot.closed { background: var(--text-secondary); }
    .empty-table { padding: 40px; text-align: center; color: var(--text-secondary); font-style: italic; }
  `]
})
export class ActiveTradePage implements OnInit, OnDestroy {
  private dashboardService = inject(DashboardService);
  private strategyService = inject(StrategyService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  activeStrategy = signal<Partial<Strategy> | null>(null);
  monitorData = signal<MonitorData | null>(null);
  currentPrice = signal(0);

  ngOnInit(): void {
    // 1. Carica info base strategia attiva
    this.sub.add(
      this.dashboardService.getStats().subscribe(data => {
        this.activeStrategy.set(data.active_strategy);
        
        // 2. Se c'è una strategia attiva, avvia il polling del monitoraggio (ogni 5 secondi)
        if (data.active_strategy?.id) {
          this.startMonitoring(data.active_strategy.id);
        }
      })
    );

    // 3. Prezzi real-time via WebSocket
    this.sub.add(
      this.wsService.on<WsPricePayload>(WsMessageType.Price).subscribe(msg => {
        if (msg.payload) this.currentPrice.set(msg.payload.price);
      })
    );
  }

  private startMonitoring(id: string) {
    this.sub.add(
      interval(5000).pipe(
        startWith(0),
        switchMap(() => this.strategyService.getMonitorData(id))
      ).subscribe(data => {
        this.monitorData.set(data);
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}