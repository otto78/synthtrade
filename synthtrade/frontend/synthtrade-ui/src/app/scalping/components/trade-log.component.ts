/**
 * Trade Log Component
 * Displays trade history — updated in real-time via WS events.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { DatePipe, DecimalPipe, NgClass, NgForOf, NgIf } from '@angular/common';
import { Subscription } from 'rxjs';
import { ScalpingWsService, TradeClosedEvent } from '../services/scalping-ws.service';

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
  `],
})
export class TradeLogComponent implements OnInit, OnDestroy {
  trades: TradeClosedEvent[] = [];
  private sub?: Subscription;

  constructor(
    private ws: ScalpingWsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.sub = this.ws.tradeClosed$.subscribe((trade) => {
      this.trades = [trade, ...this.trades];
      this.cdr.detectChanges();
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}