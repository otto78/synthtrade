import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { NgClass, DatePipe, DecimalPipe } from '@angular/common';
import { LogService } from '../../core/services/log.service';
import { TradeService } from '../../core/services/trade.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType } from '../../core/models/ws-message.model';
import { OperationLog, LogFilters, LogLevel } from '../../core/models/log.model';
import { TradeWithStrategy, TradeStrategyInfo } from '../../core/models/trade.model';
import { BadgeStatusComponent } from '../../shared/components/badge-status/badge-status.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';

const PAGE_SIZE = 50;

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [NgClass, DatePipe, DecimalPipe, BadgeStatusComponent, RelativeTimePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="logs-page">
      <!-- Tab Toggle -->
      <div class="tab-bar">
        <button class="tab-btn" [class.active]="activeTab() === 'logs'" (click)="switchTab('logs')">⚙️ Log</button>
        <button class="tab-btn" [class.active]="activeTab() === 'trades'" (click)="switchTab('trades')">📊 Storico Trade</button>
      </div>

      @if (activeTab() === 'logs') {
        <!-- LOGS VIEW -->
        <div class="logs-toolbar">
          <select class="filter-select" (change)="onFilterChange($event)">
            <option value="">Tutti</option>
            @for (level of levels; track level) {
              <option [value]="level">{{ level }}</option>
            }
          </select>
        </div>

        <div class="log-list">
          @for (log of logs(); track log.id) {
            <div class="log-row">
              <span class="log-time">{{ log.created_at | relativeTime }}</span>
              <app-badge-status [status]="log.action" />
              <span class="log-reason">{{ log.reason ?? '—' }}</span>
              @if (log.price) {
                <span class="log-price">{{ log.price }}</span>
              }
            </div>
          }
        </div>

        <div class="pagination">
          <button class="btn-prev" [disabled]="offset() === 0" (click)="prevPage()">‹ Prev</button>
          <span class="page-info">{{ offset() / pageSize + 1 }}</span>
          <button class="btn-next" (click)="nextPage()">Next ›</button>
        </div>
      }

      @if (activeTab() === 'trades') {
        <!-- TRADES VIEW -->
        <div class="logs-toolbar">
          <select class="filter-select" (change)="onTradeActionFilter($event)">
            <option value="">Tutti i tipi</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
          <select class="filter-select" (change)="onTradeStrategyFilter($event)">
            <option value="">Tutte le strategie</option>
            @for (strat of tradeStrategies(); track strat.id) {
              <option [value]="strat.id">{{ strat.title ?? '(cancellata)' }}</option>
            }
          </select>
        </div>

        @if (trades().length === 0) {
          <div class="empty-state">Nessun trade chiuso trovato.</div>
        } @else {
          <div class="trades-table-wrapper">
            <table class="trades-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Strategia</th>
                  <th>Pair</th>
                  <th>Tipo</th>
                  <th>Prezzo</th>
                  <th>Exit</th>
                  <th>Q.tà</th>
                  <th>P&L %</th>
                  <th>P&L €</th>
                </tr>
              </thead>
              <tbody>
                @for (t of trades(); track t.id) {
                  <tr>
                    <td class="cell-date">{{ t.executed_at | date:'dd/MM/yy HH:mm' }}</td>
                    <td class="cell-strategy">{{ t.strategy_title ?? '(cancellata)' }}</td>
                    <td class="cell-pair">{{ t.pair }}</td>
                    <td class="cell-side" [ngClass]="{ buy: t.action === 'BUY', sell: t.action === 'SELL' }">{{ t.action }}</td>
                    <td class="cell-price">{{ t.price | number:'1.2-2' }}</td>
                    <td class="cell-exit">{{ t.exit_price != null ? (t.exit_price | number:'1.2-2') : '—' }}</td>
                    <td class="cell-qty">{{ t.quantity | number:'1.4-4' }}</td>
                    <td class="cell-pnl" [ngClass]="{ positive: (t.pnl_pct ?? 0) >= 0, negative: (t.pnl_pct ?? 0) < 0 }">
                      {{ t.pnl_pct != null ? (t.pnl_pct | number:'1.2-2') + '%' : '—' }}
                    </td>
                    <td class="cell-pnl-eur" [ngClass]="{ positive: (t.pnl_eur ?? 0) >= 0, negative: (t.pnl_eur ?? 0) < 0 }">
                      {{ t.pnl_eur != null ? (t.pnl_eur | number:'1.2-2') + ' €' : '—' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <div class="pagination">
            <button class="btn-prev" [disabled]="tradeOffset() === 0" (click)="prevTradePage()">‹ Prev</button>
            <span class="page-info">{{ tradeOffset() / pageSize + 1 }}</span>
            <button class="btn-next" (click)="nextTradePage()">Next ›</button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .tab-bar { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid var(--border-default); }
    .tab-btn { background: none; border: none; padding: 10px 20px; font-size: 14px; font-weight: 600; color: var(--text-secondary); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
    .tab-btn.active { color: var(--accent-primary); border-bottom-color: var(--accent-primary); }
    .tab-btn:hover { color: var(--text-primary); }
    .logs-toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .filter-select { background: var(--bg-elevated); border: 1px solid var(--border-default); color: var(--text-primary); padding: 6px 12px; border-radius: 4px; font-size: 13px; }
    .log-list { display: flex; flex-direction: column; gap: 4px; }
    .log-row { display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: var(--bg-surface); border-radius: 4px; font-size: 13px; }
    .log-time { color: var(--text-muted); font-family: monospace; font-size: 11px; min-width: 60px; }
    .log-reason { flex: 1; color: var(--text-secondary); }
    .log-price { font-family: monospace; color: var(--text-primary); }
    .empty-state { padding: 40px 0; text-align: center; color: var(--text-muted); font-size: 14px; }
    .trades-table-wrapper { overflow-x: auto; }
    .trades-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .trades-table th { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border-default); color: var(--text-secondary); font-weight: 600; white-space: nowrap; }
    .trades-table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
    .trades-table tbody tr:hover { background: rgba(255,255,255,0.02); }
    .cell-date { color: var(--text-muted); font-family: monospace; font-size: 11px; white-space: nowrap; }
    .cell-strategy { color: var(--text-primary); max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cell-pair { font-family: monospace; color: var(--text-primary); font-weight: 600; }
    .cell-side { font-weight: 700; font-size: 11px; text-transform: uppercase; }
    .cell-side.buy { color: var(--color-buy); }
    .cell-side.sell { color: var(--color-sell); }
    .cell-price, .cell-exit, .cell-qty { font-family: monospace; color: var(--text-primary); }
    .cell-pnl, .cell-pnl-eur { font-family: monospace; font-weight: 700; }
    .positive { color: var(--color-buy); }
    .negative { color: var(--color-sell); }
    .pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; justify-content: flex-end; }
    .btn-prev, .btn-next { background: none; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 4px 12px; border-radius: 4px; cursor: pointer; }
    .btn-prev:disabled { opacity: 0.3; cursor: not-allowed; }
    .page-info { color: var(--text-muted); font-size: 13px; }
  `]
})
export class LogsPage implements OnInit, OnDestroy {
  private logService = inject(LogService);
  private tradeService = inject(TradeService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  readonly levels: LogLevel[] = ['BUY', 'SELL', 'SKIP', 'BLOCK', 'ERROR'];
  readonly pageSize = PAGE_SIZE;

  // Tab state
  activeTab = signal<'logs' | 'trades'>('logs');

  // Logs state
  logs = signal<OperationLog[]>([]);
  offset = signal(0);
  private activeFilter: LogLevel | undefined = undefined;

  // Trades state
  trades = signal<TradeWithStrategy[]>([]);
  tradeOffset = signal(0);
  tradeStrategies = signal<TradeStrategyInfo[]>([]);
  private tradeActionFilter: string | undefined = undefined;
  private tradeStrategyFilter: string | undefined = undefined;

  ngOnInit(): void {
    this.load();
    this.loadTradeStrategies();
    this.sub.add(
      this.wsService.on<OperationLog>(WsMessageType.NewLog).subscribe(msg => {
        if (msg.payload) this.logs.update(list => [msg.payload!, ...list]);
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }

  // ── Tab switching ──

  switchTab(tab: 'logs' | 'trades'): void {
    this.activeTab.set(tab);
    if (tab === 'trades') {
      this.loadTrades();
      this.loadTradeStrategies();
    } else {
      this.load();
    }
  }

  // ── Logs filters + pagination ──

  onFilterChange(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as LogLevel | '';
    this.activeFilter = val || undefined;
    this.offset.set(0);
    this.load();
  }

  nextPage(): void {
    this.offset.update(o => o + PAGE_SIZE);
    this.load();
  }

  prevPage(): void {
    this.offset.update(o => Math.max(0, o - PAGE_SIZE));
    this.load();
  }

  private load(): void {
    const filters: LogFilters = { limit: PAGE_SIZE, offset: this.offset() };
    if (this.activeFilter) filters.action = this.activeFilter;
    this.logService.getLogs(filters).subscribe(data => this.logs.set(data));
  }

  // ── Trades filters + pagination ──

  onTradeActionFilter(event: Event): void {
    this.tradeActionFilter = (event.target as HTMLSelectElement).value || undefined;
    this.tradeOffset.set(0);
    this.loadTrades();
  }

  onTradeStrategyFilter(event: Event): void {
    this.tradeStrategyFilter = (event.target as HTMLSelectElement).value || undefined;
    this.tradeOffset.set(0);
    this.loadTrades();
  }

  nextTradePage(): void {
    this.tradeOffset.update(o => o + PAGE_SIZE);
    this.loadTrades();
  }

  prevTradePage(): void {
    this.tradeOffset.update(o => Math.max(0, o - PAGE_SIZE));
    this.loadTrades();
  }

  private loadTrades(): void {
    this.tradeService.getTrades({
      status: 'CLOSED',
      action: this.tradeActionFilter,
      strategy_id: this.tradeStrategyFilter,
      limit: PAGE_SIZE,
      offset: this.tradeOffset(),
    }).subscribe(data => this.trades.set(data));
  }

  private loadTradeStrategies(): void {
    this.tradeService.getStrategies().subscribe(data => this.tradeStrategies.set(data));
  }
}