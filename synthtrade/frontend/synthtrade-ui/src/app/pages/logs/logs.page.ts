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
import { ScalpingSessionLogsService } from './logs.service';
import { ScalpingSessionLog, SessionTradeLog } from './logs.model';

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
        <button class="tab-btn" [class.active]="activeTab() === 'scalping'" (click)="switchTab('scalping')">🧵 Scalping</button>
        <button class="tab-btn" [class.active]="activeTab() === 'logs'" (click)="switchTab('logs')">⚙️ Log</button>
        <button class="tab-btn" [class.active]="activeTab() === 'trades'" (click)="switchTab('trades')">📊 Storico Trade</button>
      </div>

      @if (activeTab() === 'logs') {
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
              @if (log.price) { <span class="log-price">{{ log.price }}</span> }
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
                  <th>Data</th><th>Strategia</th><th>Pair</th><th>Tipo</th>
                  <th>Prezzo</th><th>Exit</th><th>Q.tà</th><th>P&L %</th><th>P&L €</th>
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

      @if (activeTab() === 'scalping') {
        @if (sessions().length === 0) {
          <div class="empty-state">Nessuna sessione di scalping trovata.</div>
        } @else {
          <div class="sessions-list">
            <!-- Header fisso -->
            <div class="session-header">
              <span></span>
              <span>Simbolo</span>
              <span>Modo</span>
              <span>Inizio</span>
              <span>Fine</span>
              <span>Durata</span>
              <span style="text-align:center">Trade</span>
              <span style="text-align:center">Wins</span>
              <span style="text-align:right">P&L</span>
              <span style="text-align:right">P&L%</span>
              <span style="text-align:right">Win%</span>
              <span style="text-align:right">vs Hold</span>
              <span></span>
            </div>

            @for (s of pagedSessions(); track s.id) {
              <div class="session-row" [class.expanded]="expandedSessionId() === s.id" (click)="toggleSession(s.id)">
                <span class="status-dot" [class.running]="s.status === 'running'" [class.stopped]="s.status !== 'running'"></span>
                <span class="session-symbol">{{ s.symbol }}</span>
                <span class="mode-badge" [class.live]="s.mode === 'LIVE'" [class.paper]="s.mode !== 'LIVE'">{{ s.mode }}</span>
                <span class="session-start">{{ s.started_at | date:'dd/MM/yy HH:mm' }}</span>
                @if (s.status === 'running') {
                  <span class="session-end">In corso</span>
                } @else {
                  <span class="session-end">{{ s.stopped_at | date:'dd/MM/yy HH:mm' }}</span>
                }
                <span class="session-duration">{{ calcDuration(s.started_at, s.stopped_at) }}</span>
                <span class="session-trades">{{ s.trade_count }}</span>
                <span class="session-wins">{{ s.win_count }}/{{ s.trade_count }}</span>
                <span class="session-pnl" [ngClass]="{ positive: s.total_pnl >= 0, negative: s.total_pnl < 0 }">
                  {{ s.total_pnl >= 0 ? '+' : '' }}{{ s.total_pnl | number:'1.2-2' }} {{ quoteAssetFromSymbol(s.symbol) }}
                </span>
                <span class="session-pnl-pct" [ngClass]="{ positive: (s.total_pnl_pct ?? 0) >= 0, negative: (s.total_pnl_pct ?? 0) < 0 }">
                  {{ s.total_pnl_pct != null ? ((s.total_pnl_pct >= 0 ? '+' : '') + (s.total_pnl_pct | number:'1.2-2') + '%') : '—' }}
                </span>
                <span class="session-winrate" [ngClass]="{ positive: winRate(s) >= 50, negative: winRate(s) < 50 }">
                  {{ s.trade_count > 0 ? (winRate(s) | number:'1.1-1') + '%' : '—' }}
                </span>
                <span class="session-hold" [ngClass]="{ positive: (s.hold_pnl_pct ?? 0) >= 0, negative: (s.hold_pnl_pct ?? 0) < 0 }">
                  {{ s.hold_pnl_pct != null ? ((s.hold_pnl_pct >= 0 ? '+' : '') + (s.hold_pnl_pct | number:'1.2-2') + '%') : '—' }}
                </span>
                <span class="expand-arrow" [class.open]="expandedSessionId() === s.id">&#8250;</span>
              </div>

              @if (expandedSessionId() === s.id) {
                <div class="session-detail">
                  @if (sessionTrades().length === 0) {
                    <div class="empty-state">Nessun trade in questa sessione.</div>
                  } @else {
                    <div class="trades-table-wrapper">
                      <table class="trades-table">
                        <thead>
                          <tr>
                            <th>Ora</th><th>Pair</th><th>Tipo</th><th>Entry</th><th>Exit</th>
                            <th>Q.tà</th><th>Durata</th><th>P&L</th><th>P&L %</th><th>Motivo</th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (t of sessionTrades(); track trackByTrade($index, t)) {
                            <tr>
                              <td class="cell-date">{{ t.entry_time | date:'HH:mm' }}</td>
                              <td class="cell-pair">{{ t.symbol }}</td>
                              <td class="cell-side" [ngClass]="{ buy: t.side === 'BUY', sell: t.side === 'SELL' }">{{ t.side }}</td>
                              <td class="cell-price">{{ t.entry_price | number:'1.2-6' }}</td>
                              <td class="cell-exit">{{ t.exit_price != null ? (t.exit_price | number:'1.2-6') : '—' }}</td>
                              <td class="cell-qty">{{ t.quantity | number:'1.4-8' }}</td>
                              <td class="cell-duration">{{ tradeDuration(t.entry_time, t.exit_time) }}</td>
                              <td class="cell-pnl-eur" [ngClass]="{ positive: (t.pnl ?? 0) >= 0, negative: (t.pnl ?? 0) < 0 }">
                                {{ t.pnl != null ? ((t.pnl >= 0 ? '+' : '') + (t.pnl | number:'1.2-2') + ' ' + quoteAssetFromSymbol(t.symbol)) : '—' }}
                              </td>
                              <td class="cell-pnl" [ngClass]="{ positive: (t.pnl_pct ?? 0) >= 0, negative: (t.pnl_pct ?? 0) < 0 }">
                                {{ t.pnl_pct != null ? ((t.pnl_pct >= 0 ? '+' : '') + (t.pnl_pct | number:'1.2-2') + '%') : '—' }}
                              </td>
                              <td class="cell-reason">{{ t.signal_reason ?? '—' }}</td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  }
                </div>
              }
            }

            <!-- Paginazione sessioni -->
            @if (sessions().length > sessionsPageSize) {
              <div class="pagination">
                <button class="btn-prev" [disabled]="sessionsPage() === 0" (click)="prevSessionPage()">‹ Prev</button>
                <span class="page-info">{{ sessionsPage() + 1 }} / {{ totalSessionPages() }}</span>
                <button class="btn-next" [disabled]="sessionsPage() >= totalSessionPages() - 1" (click)="nextSessionPage()">Next ›</button>
              </div>
            }
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
    .cell-duration { font-family: monospace; font-size: 11px; color: var(--text-muted); white-space: nowrap; }
    .cell-reason { font-size: 11px; color: var(--text-secondary); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .positive { color: var(--color-buy); }
    .negative { color: var(--color-sell); }
    .pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; justify-content: flex-end; }
    .btn-prev, .btn-next { background: none; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 4px 12px; border-radius: 4px; cursor: pointer; }
    .btn-prev:disabled { opacity: 0.3; cursor: not-allowed; }
    .page-info { color: var(--text-muted); font-size: 13px; }
    /* Scalping accordion */
    .sessions-list { display: flex; flex-direction: column; width: 100%; }
      .session-header, .session-row {
      display: grid;
      grid-template-columns: 2% 12% 6% 12% 12% 9% 5% 5% 10% 7% 7% 8% 5%;
      gap: 0;
      align-items: center;
      width: 100%;
      box-sizing: border-box;
      padding: 12px 20px;
    }
    .session-header {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.4px;
      border-bottom: 1px solid var(--border-default);
      margin-bottom: 6px;
      padding-bottom: 10px;
    }
    .session-row {
      background: var(--bg-surface);
      border: 1px solid var(--border-default);
      border-radius: 8px;
      margin-bottom: 6px;
      cursor: pointer;
      font-size: 15px;
      transition: background 0.15s;
    }
    .session-row:hover { background: rgba(255,255,255,0.04); }
    .session-row.expanded { border-color: var(--accent-primary); border-bottom-left-radius: 0; border-bottom-right-radius: 0; margin-bottom: 0; }
    .status-dot { width: 10px; height: 10px; border-radius: 50%; justify-self: center; }
    .status-dot.running { background: #26a69a; box-shadow: 0 0 6px rgba(38,166,154,0.5); }
    .status-dot.stopped { background: #555; }
    .session-symbol { font-family: monospace; font-weight: 700; font-size: 14px; color: var(--text-primary); }
    .mode-badge { font-size: 11px; font-weight: 700; padding: 3px 7px; border-radius: 3px; text-transform: uppercase; justify-self: start; }
    .mode-badge.live { background: rgba(38,166,154,0.2); color: #26a69a; }
    .mode-badge.paper { background: rgba(38,166,154,0.2); color: #26a69a; }
    .session-start, .session-end { font-family: monospace; font-size: 12px; color: var(--text-muted); }
    .session-duration { font-family: monospace; font-size: 13px; color: var(--text-secondary); }
    .session-trades, .session-wins { font-size: 13px; color: var(--text-secondary); text-align: center; }
    .session-pnl { font-family: monospace; font-weight: 700; font-size: 14px; text-align: right; white-space: nowrap; }
    .session-pnl-pct { font-family: monospace; font-weight: 600; font-size: 13px; text-align: right; }
    .session-winrate, .session-hold { font-family: monospace; font-weight: 600; font-size: 13px; text-align: right; }
    .expand-arrow {
      font-size: 22px; text-align: right; justify-self: end;
      font-weight: 600; color: var(--text-muted);
      transition: transform 0.2s ease; line-height: 1;
      display: inline-block; padding: 0 4px;
    }
    .expand-arrow.open { transform: rotate(90deg); color: var(--accent-primary); }
    .session-detail { background: var(--bg-elevated); border: 1px solid var(--accent-primary); border-top: none; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; padding: 12px; margin-bottom: 6px; }
  `]
})
export class LogsPage implements OnInit, OnDestroy {
  private logService = inject(LogService);
  private tradeService = inject(TradeService);
  private wsService = inject(WsService);
  private scalpingSessionLogsService = inject(ScalpingSessionLogsService);
  private sub = new Subscription();

  readonly levels: LogLevel[] = ['BUY', 'SELL', 'SKIP', 'BLOCK', 'ERROR'];
  readonly pageSize = PAGE_SIZE;

  activeTab = signal<'logs' | 'trades' | 'scalping'>('scalping');

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

  // Scalping sessions state
  sessions = signal<ScalpingSessionLog[]>([]);
  expandedSessionId = signal<string | null>(null);
  sessionTrades = signal<SessionTradeLog[]>([]);
  private sessionsLoaded = false;
  readonly sessionsPageSize = 10;
  sessionsPage = signal(0);

  pagedSessions(): ScalpingSessionLog[] {
    const start = this.sessionsPage() * this.sessionsPageSize;
    return this.sessions().slice(start, start + this.sessionsPageSize);
  }

  totalSessionPages(): number {
    return Math.ceil(this.sessions().length / this.sessionsPageSize);
  }

  nextSessionPage(): void { this.sessionsPage.update(p => p + 1); }
  prevSessionPage(): void { this.sessionsPage.update(p => Math.max(0, p - 1)); }

  ngOnInit(): void {
    this.loadSessions();
    this.load();
    this.loadTradeStrategies();
    this.sub.add(
      this.wsService.on<OperationLog>(WsMessageType.NewLog).subscribe(msg => {
        const payload = msg.payload;
        if (payload) this.logs.update(list => [payload, ...list]);
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }

  switchTab(tab: 'logs' | 'trades' | 'scalping'): void {
    this.activeTab.set(tab);
    if (tab === 'scalping') {
      if (!this.sessionsLoaded) this.loadSessions();
      this.expandedSessionId.set(null);
      this.sessionTrades.set([]);
      this.sessionsPage.set(0);
    } else if (tab === 'trades') {
      this.loadTrades();
      this.loadTradeStrategies();
    } else {
      this.load();
    }
  }

  // ── Logs ──

  onFilterChange(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as LogLevel | '';
    this.activeFilter = val || undefined;
    this.offset.set(0);
    this.load();
  }

  nextPage(): void { this.offset.update(o => o + PAGE_SIZE); this.load(); }
  prevPage(): void { this.offset.update(o => Math.max(0, o - PAGE_SIZE)); this.load(); }

  private load(): void {
    const filters: LogFilters = { limit: PAGE_SIZE, offset: this.offset() };
    if (this.activeFilter) filters.action = this.activeFilter;
    this.logService.getLogs(filters).subscribe(data => this.logs.set(data));
  }

  // ── Trades ──

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

  nextTradePage(): void { this.tradeOffset.update(o => o + PAGE_SIZE); this.loadTrades(); }
  prevTradePage(): void { this.tradeOffset.update(o => Math.max(0, o - PAGE_SIZE)); this.loadTrades(); }

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

  // ── Scalping sessions ──

  private loadSessions(): void {
    this.scalpingSessionLogsService.getSessions().subscribe(data => {
      this.sessions.set(data);
      this.sessionsLoaded = true;
    });
  }

  toggleSession(sessionId: string): void {
    if (this.expandedSessionId() === sessionId) {
      this.expandedSessionId.set(null);
      this.sessionTrades.set([]);
    } else {
      this.expandedSessionId.set(sessionId);
      this.sessionTrades.set([]);
      this.scalpingSessionLogsService.getSessionTrades(sessionId).subscribe(data => {
        this.sessionTrades.set(data);
        // Calcola Win vs Hold: (exit_price del primo trade / entry_price del primo trade - 1) * 100
        // Proxy semplice: se avessi tenuto invece di tradare
        if (data.length > 0) {
          const sorted = [...data].sort((a, b) => a.entry_time.localeCompare(b.entry_time));
          const first = sorted[0];
          const last = sorted[sorted.length - 1];
          if (first.entry_price && last.exit_price) {
            const holdPct = ((last.exit_price - first.entry_price) / first.entry_price) * 100;
            this.sessions.update(list => list.map(s =>
              s.id === sessionId ? { ...s, hold_pnl_pct: Math.round(holdPct * 100) / 100 } : s
            ));
          }
        }
      });
    }
  }

  // ── Helpers ──

  winRate(s: ScalpingSessionLog): number {
    return s.trade_count > 0 ? (s.win_count / s.trade_count) * 100 : 0;
  }

  calcDuration(startIso: string, endIso?: string): string {
    const start = new Date(startIso).getTime();
    const end = endIso ? new Date(endIso).getTime() : Date.now();
    const sec = Math.floor((end - start) / 1000);
    if (sec >= 86400) return `${Math.floor(sec / 86400)}g ${Math.floor((sec % 86400) / 3600)}h`;
    if (sec >= 3600) return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`;
    if (sec >= 60) return `${Math.floor(sec / 60)}m ${sec % 60}s`;
    return `${sec}s`;
  }

  tradeDuration(entryIso: string, exitIso?: string): string {
    if (!exitIso) return 'aperto';
    const sec = Math.floor((new Date(exitIso).getTime() - new Date(entryIso).getTime()) / 1000);
    if (sec >= 3600) return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`;
    if (sec >= 60) return `${Math.floor(sec / 60)}m ${sec % 60}s`;
    return `${sec}s`;
  }

  quoteAssetFromSymbol(symbol: string): string {
    if (symbol.endsWith('USDC')) return 'USDC';
    if (symbol.endsWith('EUR')) return 'EUR';
    if (symbol.endsWith('FDUSD')) return 'FDUSD';
    return 'USDT';
  }

  trackByTrade(index: number, trade: SessionTradeLog): string {
    return trade.entry_time + trade.symbol + trade.side;
  }
}
