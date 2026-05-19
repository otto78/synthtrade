import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule, NgClass, NgForOf, NgIf, DatePipe, DecimalPipe } from '@angular/common';
import { Subscription, switchMap, forkJoin, of, catchError, map } from 'rxjs';
import { DashboardService } from '../../core/services/dashboard.service';
import { StrategyService, ActivePnlItem, MonitorStrategyInfo } from '../../core/services/strategy.service';
import { WsService } from '../../core/services/ws.service';
import {
  WsMessageType,
  WsStrategyPnlUpdatedPayload,
  WsStrategyStoppedPayload,
  WsTradeOpenedPayload,
  WsTradeClosedPayload
} from '../../core/models/ws-message.model';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { ActiveTradeRowComponent, ActiveTradeRowData } from '../../shared/components/active-trade-row/active-trade-row.component';

interface TradeDetail {
  id: string;
  executed_at: string;
  symbol: string;
  side: string;
  pnl_pct: number;
  price: number;
  quantity: number;
  status: string;
  trade_type: string;
  strategy_id: string;
}

interface StrategyActiveInfo {
  id: string;
  title: string;
  pair: string;
  timeframe: string;
  initial_capital_usdt: number;
  pnl_pct: number;
  pnl_eur: number;
  open_trades: TradeDetail[];
  closed_trades: TradeDetail[];
  equity_curve: number[];
}

@Component({
  selector: 'app-active-trade',
  standalone: true,
  imports: [NgClass, NgIf, NgForOf, EmptyStateComponent, DatePipe, DecimalPipe, ActiveTradeRowComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ng-container *ngIf="strategies().length === 0; else activeTradeList">
      <app-empty-state message="Nessun trade attivo" icon="📊"></app-empty-state>
    </ng-container>

    <ng-template #activeTradeList>
      <div class="active-trade">
        <h1 class="page-title">📈 Trade Attivi ({{ strategies().length }} strategie attive)</h1>

        <!-- KPIs Globali -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <span class="kpi-label">Strategie Attive</span>
            <div class="kpi-main highlight">{{ strategies().length }}</div>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">Trade Aperti Totali</span>
            <div class="kpi-main highlight">{{ totalOpenTrades() }}</div>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">P&L Cumulativo</span>
            <div class="kpi-main" [ngClass]="{ positive: totalPnl() > 0, negative: totalPnl() < 0 }">
              {{ totalPnl() | number:'1.2-2' }}%
            </div>
          </div>
        </div>

        <!-- Lista Strategie Attive -->
        <div class="strategies-list">
          <ng-container *ngFor="let s of strategies(); trackBy: trackByStrategy">
            <div class="strategy-section">
              <div class="section-header" (click)="toggleCollapse(s.id)">
                <span class="collapse-indicator">{{ collapsed()[s.id] ? '▸' : '▾' }}</span>
                <div class="section-title-row">
                  <span class="section-title">{{ s.title }}</span>
                  <span class="section-meta">{{ s.pair }} · {{ s.timeframe }}</span>
                </div>
                <div class="section-stats">
                  <div class="ss-item">
                    <span class="ss-label">Capitale</span>
                    <span class="ss-value">{{ s.initial_capital_usdt | number:'1.0-0' }} USDT</span>
                  </div>
                  <div class="ss-item">
                    <span class="ss-label">P&L</span>
                    <span class="ss-value" [ngClass]="{ positive: s.pnl_pct > 0, negative: s.pnl_pct < 0 }">
                      {{ s.pnl_pct | number:'1.2-2' }}%
                    </span>
                  </div>
                  <div class="ss-item">
                    <span class="ss-label">Trade Aperti</span>
                    <span class="ss-value highlight">{{ s.open_trades.length }}</span>
                  </div>
                </div>
              </div>

              <div *ngIf="!collapsed()[s.id]">
                <div *ngIf="s.open_trades.length > 0" class="trades-section">
                  <h4 class="subsection-title">🟢 Trade Aperti</h4>
                  <div class="trades-table">
                    <div class="table-header">
                      <span>Data</span>
                      <span>Asset</span>
                      <span>Direzione</span>
                      <span>Q.tà</span>
                      <span>Prezzo Entry</span>
                      <span>P&L</span>
                      <span>Valore</span>
                    </div>
                    <ng-container *ngFor="let trade of s.open_trades; trackBy: trackByTrade">
                      <app-active-trade-row [tradeData]="toActiveTradeRowData(trade, s)"></app-active-trade-row>
                    </ng-container>
                  </div>
                </div>

                <div *ngIf="s.closed_trades.length > 0" class="trades-section">
                  <h4 class="subsection-title">🔵 Trade Chiusi</h4>
                  <div class="trades-table">
                    <div class="table-header">
                      <span>Data</span>
                      <span>Asset</span>
                      <span>Direzione</span>
                      <span>P&L</span>
                      <span>Tipo</span>
                      <span>Stato</span>
                    </div>
                    <ng-container *ngFor="let trade of s.closed_trades; trackBy: trackByTrade">
                      <div class="table-row">
                        <span class="cell-date">{{ trade.executed_at | date:'dd/MM HH:mm' }}</span>
                        <span class="cell-asset">{{ trade.symbol }}</span>
                        <span class="cell-side" [ngClass]="trade.side.toLowerCase()">{{ trade.side }}</span>
                        <span class="cell-pnl" [ngClass]="{ positive: trade.pnl_pct > 0, negative: trade.pnl_pct < 0 }">
                          {{ trade.pnl_pct | number:'1.2-2' }}%
                        </span>
                        <span class="cell-type">{{ trade.trade_type }}</span>
                        <span class="cell-status">
                          <span class="status-dot closed"></span>
                          {{ trade.status }}
                        </span>
                      </div>
                    </ng-container>
                  </div>
                </div>

                <div *ngIf="s.equity_curve.length > 1" class="chart-section">
                  <h4 class="subsection-title">📈 Equity Curve</h4>
                  <div class="equity-viz">
                    <div class="curve-points">
                      <div *ngFor="let point of s.equity_curve; index as i" class="point-bar" [style.height.%]="point" [title]="point.toFixed(2) + '%'">
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </ng-container>
        </div>
      </div>
    </ng-template>
  `,
  styles: [`
    .active-trade { padding: 24px; max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; }
    .page-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
    .kpi-card { background: var(--bg-card); border: 1px solid var(--border-default); padding: 20px; border-radius: 12px; }
    .kpi-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; display: block; }
    .kpi-main { font-size: 24px; font-weight: 700; font-family: monospace; color: var(--text-primary); }
    .kpi-main.highlight { color: var(--accent-primary); }
    .positive { color: var(--color-buy); }
    .negative { color: var(--color-sell); }
    .strategies-list { display: flex; flex-direction: column; gap: 24px; }
    .strategy-section { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 16px; padding: 24px; }
    .section-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border-default); }
    .section-title-row { display: flex; flex-direction: column; gap: 4px; }
    .section-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
    .section-meta { font-size: 13px; color: var(--text-secondary); font-family: monospace; }
    .section-stats { display: flex; gap: 24px; }
    .ss-item { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
    .ss-label { font-size: 9px; color: var(--text-muted); text-transform: uppercase; }
    .ss-value { font-size: 15px; font-weight: 700; font-family: monospace; }
    .ss-value.highlight { color: var(--accent-primary); }
    .subsection-title { font-size: 14px; font-weight: 600; color: var(--text-secondary); margin: 0 0 12px 0; }
    .trades-section { margin-bottom: 20px; }
    .trades-table { display: flex; flex-direction: column; }
    .table-header { display: grid; grid-template-columns: 1.2fr 1fr 0.6fr 0.8fr 1fr 1fr 1fr; padding: 12px; border-bottom: 1px solid var(--border-default); color: var(--text-secondary); font-size: 12px; font-weight: 600; }
    .table-row { display: grid; grid-template-columns: 1.2fr 1fr 0.8fr 0.8fr 1fr 1fr 0.8fr; padding: 16px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); align-items: center; transition: background 0.2s; }
    .table-row:hover { background: rgba(255,255,255,0.02); }
    .cell-date { color: var(--text-secondary); font-size: 13px; }
    .cell-asset { font-weight: 600; color: var(--text-primary); }
    .cell-qty, .cell-type { font-family: monospace; font-size: 13px; color: var(--text-primary); }
    .cell-price { font-family: monospace; font-size: 13px; color: var(--text-primary); }
    .cell-side { font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .cell-side.buy { color: var(--color-buy); }
    .cell-side.sell { color: var(--color-sell); }
    .cell-pnl { font-family: monospace; font-weight: 700; }
    .cell-status { display: flex; align-items: center; gap: 6px; font-size: 12px; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; }
    .status-dot.open { background: var(--color-buy); box-shadow: 0 0 8px var(--color-buy); }
    .status-dot.closed { background: var(--text-secondary); }
    .chart-section { margin-top: 8px; }
    .equity-viz { height: 100px; display: flex; align-items: flex-end; gap: 2px; padding-top: 12px; border-bottom: 1px solid var(--border-default); }
    .curve-points { display: flex; align-items: flex-end; gap: 2px; height: 100%; width: 100%; }
    .point-bar { flex: 1; background: var(--accent-primary); opacity: 0.6; border-radius: 2px 2px 0 0; min-width: 4px; transition: height 0.3s ease; }
    .point-bar:hover { opacity: 1; }
  `]
})
export class ActiveTradePage implements OnInit, OnDestroy {
  // Map to keep collapse state per strategy id
  collapsed = signal<Record<string, boolean>>({});

  // Toggle collapse for a given strategy
  toggleCollapse(strategyId: string): void {
    this.collapsed.update(map => ({
      ...map,
      [strategyId]: !map[strategyId]
    }));
  }

  trackByStrategy(index: number, strategy: StrategyActiveInfo): string {
    return strategy.id;
  }

  trackByTrade(index: number, trade: TradeDetail): string {
    return trade.id;
  }

  private dashboardService = inject(DashboardService);
  private strategyService = inject(StrategyService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  strategies = signal<StrategyActiveInfo[]>([]);
  private currentStrategies: StrategyActiveInfo[] = [];

  totalOpenTrades = computed(() =>
    this.strategies().reduce((acc, s) => acc + s.open_trades.length, 0)
  );

  totalPnl = computed(() => {
    const list = this.strategies();
    if (list.length === 0) return 0;
    return list.reduce((acc, s) => acc + s.pnl_pct, 0) / list.length;
  });

  ngOnInit(): void {
    this.loadActiveStrategies();
    this.setupWsListeners();
  }

  private loadActiveStrategies() {
    this.sub.add(
      this.strategyService.getActivePnl().pipe(
        switchMap(response => {
          const pnlItems: ActivePnlItem[] = response?.active_strategies_pnl || [];
          if (pnlItems.length === 0) {
            return of([] as MonitorStrategyInfo[]);
          }
          return forkJoin(
            pnlItems.map(item =>
              this.strategyService.getMonitorData(item.id).pipe(
                catchError(() => of(null))
              )
            )
          ).pipe(
            map((results: (MonitorStrategyInfo | null)[]) =>
              results.filter((r): r is MonitorStrategyInfo => r !== null)
            )
          );
        }),
        catchError(() => of([] as MonitorStrategyInfo[]))
      ).subscribe(monitorData => {
        this.currentStrategies = monitorData.map(m => this.buildStrategyInfo(m));
        this.strategies.set(this.currentStrategies);
      })
    );
  }

  private buildStrategyInfo(monitor: MonitorStrategyInfo): StrategyActiveInfo {
    const openTrades: TradeDetail[] = (monitor.recent_trades || [])
      .filter(t => t.status === 'OPEN')
      .map(t => ({
        id: t.id,
        executed_at: t.executed_at,
        symbol: t.pair || t.symbol || '',
        side: t.action || t.side || '',
        pnl_pct: t.pnl_pct || 0,
        price: t.price || 0,
        quantity: t.quantity || 0,
        status: t.status,
        trade_type: t.trade_type || 'SIGNAL',
        strategy_id: t.strategy_id || monitor.strategy?.id || ''
      }));

    const closedTrades: TradeDetail[] = (monitor.recent_trades || [])
      .filter(t => t.status === 'CLOSED')
      .map(t => ({
        id: t.id,
        executed_at: t.executed_at,
        symbol: t.pair || t.symbol || '',
        side: t.action || t.side || '',
        pnl_pct: t.pnl_pct || 0,
        price: t.price || 0,
        quantity: t.quantity || 0,
        status: t.status,
        trade_type: t.trade_type || 'SIGNAL',
        strategy_id: t.strategy_id || monitor.strategy?.id || ''
      }));

    return {
      id: monitor.strategy?.id || '',
      title: monitor.strategy?.title || '',
      pair: monitor.strategy?.pair || '',
      timeframe: monitor.strategy?.timeframe || '',
      initial_capital_usdt: monitor.stats?.total_pnl_eur
        ? Math.abs(monitor.stats.total_pnl_eur / ((monitor.stats.total_pnl_pct || 1) / 100))
        : 0,
      pnl_pct: monitor.stats?.total_pnl_pct || 0,
      pnl_eur: monitor.stats?.total_pnl_eur || 0,
      open_trades: openTrades,
      closed_trades: closedTrades,
      equity_curve: monitor.stats?.equity_curve || [100]
    };
  }

  private setupWsListeners(): void {
    this.sub.add(
      this.wsService.on<WsStrategyPnlUpdatedPayload>(WsMessageType.StrategyPnlUpdated).subscribe(msg => {
        const sid = msg['strategy_id'] as string | undefined;
        if (!sid) return;
        this.strategies.update(list =>
          list.map(s => {
            if (s.id === sid) {
              return {
                ...s,
                pnl_pct: (msg['current_pnl_pct'] as number | undefined) ?? s.pnl_pct,
                pnl_eur: (msg['current_pnl_eur'] as number | undefined) ?? s.pnl_eur,
              };
            }
            return s;
          })
        );
      })
    );

    this.sub.add(
      this.wsService.on<WsTradeOpenedPayload>(WsMessageType.TradeOpened).subscribe(() => {
        this.loadActiveStrategies();
      })
    );

    this.sub.add(
      this.wsService.on<WsTradeClosedPayload>(WsMessageType.TradeClosed).subscribe(() => {
        this.loadActiveStrategies();
      })
    );

    this.sub.add(
      this.wsService.on<WsStrategyStoppedPayload>(WsMessageType.StrategyStopped).subscribe(msg => {
        const sid = msg['strategy_id'] as string | undefined;
        if (sid) {
          this.strategies.update(list => list.filter(s => s.id !== sid));
          // also remove collapse state for this strategy
          this.collapsed.update(map => {
            const { [sid]: _, ...rest } = map;
            return rest;
          });
        }
      })
    );
  }

  /** Converte TradeDetail in ActiveTradeRowData per il componente riutilizzabile */
  toActiveTradeRowData(trade: TradeDetail, strategy: StrategyActiveInfo): ActiveTradeRowData {
    return {
      id: trade.id,
      strategy_id: strategy.id,
      strategy_title: strategy.title,
      symbol: trade.symbol,
      side: (trade.side === 'SELL' ? 'SELL' : 'BUY') as 'BUY' | 'SELL',
      entry_price: trade.price,
      current_price: trade.price,
      unrealized_pnl_pct: trade.pnl_pct,
      quantity: trade.quantity,
      opened_at: trade.executed_at,
    };
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}
