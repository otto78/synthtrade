/**
 * Trade Log Component
 * Displays trade history — updated in real-time via WS events.
 * On init, fetches historical trades from REST API to populate the log
 * when returning to the page with an active session.
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
      <h3>Trade Log</h3>

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
              <td>{{ trade.timestamp | date:'shortTime' }}</td>
              <td [ngClass]="trade.side.toLowerCase()">{{ trade.side }}</td>
              <td>{{ trade.entry_price | number:'1.2-2' }}</td>
              <td>{{ trade.exit_price | number:'1.2-2' }}</td>
              <td [ngClass]="trade.pnl >= 0 ? 'profit' : 'loss'">
                {{ trade.pnl | number:'1.2-2' }}
              </td>
              <td class="reason-cell">{{ trade.signal_reason || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .trade-log { padding: 12px; max-height: 300px; overflow-y: auto; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .no-trades { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    table { width: 100%; font-size: 11px; border-collapse: collapse; }
    th, td { text-align: left; padding: 4px 6px; }
    th { color: var(--text-secondary); font-weight: 500; border-bottom: 1px solid var(--border-default); }
    td { color: var(--text-primary); }
    .buy { color: var(--accent-success, #26a69a); }
    .sell { color: var(--accent-danger, #ef5350); }
    .profit { color: var(--accent-success, #26a69a); }
    .loss { color: var(--accent-danger, #ef5350); }
    .reason-cell { font-size: 10px; opacity: 0.8; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  `],
})
export class TradeLogComponent implements OnInit, OnDestroy {
  trades: TradeClosedEvent[] = [];
  private sub?: Subscription;
  private readonly API_URL = '/api/scalping/trade-history';

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Step 1: Clear trades when a new session starts (stop + restart)
    this.sub = this.sessionApi.session$.subscribe((session) => {
      if (!session || session.status === 'idle') {
        this.trades = [];
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      } else if (session.status === 'running') {
        // New session started — reload history (will be empty for fresh session)
        this.trades = [];
        this.cdr.markForCheck();
        this.cdr.detectChanges();
        this.loadHistory();
      }
    });

    // Step 2: Subscribe to live WS trade_closed events for real-time updates
    this.sub.add(
      this.ws.tradeClosed$.subscribe((trade) => {
        this.trades = [trade, ...this.trades];
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      })
    );

    // Step 3: No initial load — wait for active session via session$ subscription
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  private loadHistory(): void {
    this.http.get<TradeClosedEvent[]>(this.API_URL).subscribe({
      next: (history: TradeClosedEvent[]) => {
        if (history.length > 0) {
          // Reverse so oldest trades appear first, then prepend newer ones
          this.trades = history.reverse();
          this.cdr.markForCheck();
          this.cdr.detectChanges();
          console.log(`[TradeLog] Loaded ${history.length} historical trades`);
        }
      },
      error: (err: Error) => {
        console.warn('[TradeLog] Failed to load trade history:', err);
      }
    });
  }
}