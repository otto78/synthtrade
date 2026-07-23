/**
 * Trade Log Component
 * Displays trade history — updated in real-time via WS events.
 * On init, fetches historical trades from REST API to populate the log
 * when returning to the page with an active session.
 *
 * FIX-2026-06-12: Deduplicate trades by entry_price+exit_price+symbol to
 * prevent duplicates when WS trade_closed arrives after REST history load.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { DatePipe, DecimalPipe, NgClass, NgForOf, NgIf } from '@angular/common';
import { Subscription } from 'rxjs';
import { ScalpingWsService, TradeClosedEvent } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';

@Component({
  selector: 'app-trade-log',
  standalone: true,
  imports: [DatePipe, DecimalPipe, NgClass, NgForOf, NgIf],
  template: `
    <div class="trade-log">
      <span class="panel-title">Trade Log</span>
      <div class="title-hr"></div>

      <div *ngIf="trades.length === 0" class="no-trades">No trades yet</div>

      <div class="trades-list">
        <table *ngIf="trades.length > 0">
          <thead>
            <tr>
              <th>Time</th>
              <th>Side</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>PnL</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let trade of trades">
              <td>{{ trade.timestamp | date:'MM/dd HH:mm:ss' }}</td>
              <td [ngClass]="getPositionSideClass(trade)">{{ getPositionSideLabel(trade) }}</td>
              <td>{{ trade.entry_price | number:'1.2-2' }}</td>
              <td>{{ trade.exit_price | number:'1.2-2' }}</td>
              <td [ngClass]="trade.pnl >= 0 ? 'profit' : 'loss'">
                {{ trade.pnl | number:'1.2-2' }}
              </td>
              <td class="reason-cell" [ngClass]="getReasonClass(trade.signal_reason)">{{ trade.signal_reason || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .trade-log { padding: 12px; max-height: 300px; overflow-y: auto; }
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 10px 0 12px 0; }
    .no-trades { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    table { width: 100%; font-size: 11px; border-collapse: collapse; }
    th, td { text-align: left; padding: 4px 6px; }
    th { color: var(--text-secondary); font-weight: 500; border-bottom: 1px solid var(--border-default); }
    td { color: var(--text-primary); }
    .buy { color: var(--accent-success, #26a69a); }
    .sell { color: var(--accent-danger, #ef5350); }
    .long { color: var(--accent-success, #26a69a); }
    .short { color: var(--accent-danger, #ef5350); }
    .profit { color: var(--accent-success, #26a69a); }
    .loss { color: var(--accent-danger, #ef5350); }
    .reason-cell { font-size: 10px; opacity: 0.8; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .reason-stop-loss { color: var(--accent-danger, #ef5350); font-weight: 600; }
    .reason-take-profit { color: var(--accent-success, #26a69a); font-weight: 600; }
    .reason-timestop { color: #F0B90B; font-weight: 600; }
  `],
})
export class TradeLogComponent implements OnInit, OnDestroy {
  trades: TradeClosedEvent[] = [];
  private sub?: Subscription;
  private readonly API_URL = '/api/scalping/trade-history';
  /** Track seen trade keys (entry_price + exit_price + symbol) to avoid duplicates. */
  private seenKeys = new Set<string>();

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Step 1: Listen for session status changes
    this.sub = this.sessionApi.session$.subscribe((session) => {
      if (!session || session.status === 'idle') {
        this.trades = [];
        this.seenKeys.clear();
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      } else {
        // On fresh session (trades empty or seenKeys empty), clear and reload.
        // On session restore (reconnect/refresh), merge with dedup.
        if (this.trades.length === 0 || this.seenKeys.size === 0) {
          this.trades = [];
          this.seenKeys.clear();
        }
        this.loadHistory();
      }
    });

    // Step 2: Subscribe to live WS trade_closed events — deduplicate
    this.sub.add(
      this.ws.tradeClosed$.subscribe((trade) => {
        // TASK-1180: ignore ghost trades closed without a known fill (from reconciliation)
        if (trade.signal_reason === 'external_close_unknown_price') {
          return;
        }
        
        const key = `${trade.entry_price}|${trade.exit_price}|${trade.symbol}`;
        if (this.seenKeys.has(key)) {
          return; // already in the list
        }
        this.seenKeys.add(key);
        this.trades = [trade, ...this.trades];
        // Ensure chronological sort always
        this.trades.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      })
    );
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  getReasonClass(reason: string | undefined): string {
    if (!reason) return '';
    const r = reason.toLowerCase().replace(/\s+/g, '-');
    if (r.includes('stop-loss') || r.includes('stop_loss') || r === 'stop') return 'reason-stop-loss';
    if (r.includes('take-profit') || r.includes('take_profit') || r === 'tp' || r === 'take') return 'reason-take-profit';
    if (r.includes('timestop')) return 'reason-timestop';
    return '';
  }

  /** Position side label: LONG/SHORT (falls back to BUY/SELL) */
  getPositionSideLabel(trade: TradeClosedEvent): string {
    return trade.position_side ?? trade.side;
  }

  /** Position side CSS class */
  getPositionSideClass(trade: TradeClosedEvent): string {
    const ps = trade.position_side;
    if (ps === 'SHORT') return 'short';
    if (ps === 'LONG') return 'long';
    return trade.side.toLowerCase();
  }

  /** Deduplicate by unique trade key (entry_price+exit_price+symbol). */
  private deduplicate(history: TradeClosedEvent[]): TradeClosedEvent[] {
    const localSeen = new Set(this.seenKeys);
    const result: TradeClosedEvent[] = [];
    for (const trade of history) {
      const key = `${trade.entry_price}|${trade.exit_price}|${trade.symbol}`;
      if (!localSeen.has(key)) {
        localSeen.add(key);
        result.push(trade);
        this.seenKeys.add(key);
      }
    }
    return result;
  }

  private loadHistory(): void {
    this.http.get<TradeClosedEvent[]>(this.API_URL).subscribe({
      next: (history: TradeClosedEvent[]) => {
        if (history.length > 0) {
          // Merge with existing trades, deduplicating
          const newTrades = this.deduplicate(history);
          if (newTrades.length > 0) {
            // Sort by timestamp DESC
            const merged = [...this.trades, ...newTrades];
            merged.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
            this.trades = merged;
            this.cdr.markForCheck();
            this.cdr.detectChanges();
          }
          console.log(`[TradeLog] Loaded ${newTrades.length} new historical trades (${this.trades.length} total)`);
        }
      },
      error: (err: Error) => {
        console.warn('[TradeLog] Failed to load trade history:', err);
      }
    });
  }
}