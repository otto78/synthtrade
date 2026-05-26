/**
 * Trade Log Component
 * Displays trade history with signal score
 */

import { Component, OnInit } from '@angular/core';
import { DatePipe, DecimalPipe, NgClass, NgForOf, NgIf } from '@angular/common';
import { ScalpingWsService, SignalEvent } from '../services/scalping-ws.service';

export interface TradeLogEntry {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  signal_score?: number;
  opened_at: string;
  closed_at: string;
}

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
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let trade of trades">
              <td>{{ trade.opened_at | date:'shortTime' }}</td>
              <td [ngClass]="trade.side.toLowerCase()">{{ trade.side }}</td>
              <td>{{ trade.entry_price | number:'1.2-2' }}</td>
              <td>{{ trade.exit_price | number:'1.2-2' }}</td>
              <td [ngClass]="trade.pnl >= 0 ? 'profit' : 'loss'">
                {{ trade.pnl | number:'1.2-2' }}
              </td>
              <td>{{ trade.signal_score ?? '--' }}</td>
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
export class TradeLogComponent implements OnInit {
  trades: TradeLogEntry[] = [];

  constructor(private ws: ScalpingWsService) {}

  ngOnInit(): void {
    // Placeholder - will be populated from actual trade data
  }
}