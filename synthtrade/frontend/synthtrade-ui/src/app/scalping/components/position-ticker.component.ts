/**
 * Position Ticker Component
 * Shows open position from WS events (candle, position updates).
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { NgIf, NgClass, DecimalPipe, PercentPipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { ScalpingWsService, PositionEvent } from '../services/scalping-ws.service';
import { Position } from '../models/position.model';

@Component({
  selector: 'app-position-ticker',
  standalone: true,
  imports: [NgIf, NgClass, DecimalPipe, PercentPipe],
  template: `
    <div class="position-ticker">
      <h3>Position</h3>

      <div *ngIf="!position" class="no-position">
        No open position
      </div>

      <div *ngIf="position" class="position-content">
        <div class="row symbol-side">
          <span class="symbol">{{ position.symbol }}</span>
          <span class="side" [ngClass]="position.side.toLowerCase()">{{ position.side }}</span>
        </div>
        <div class="row prices">
          <span>Entry: {{ position.entry_price | number:'1.2-2' }}</span>
          <span>Current: {{ position.current_price | number:'1.2-2' }}</span>
        </div>
        <div class="row pnl" [ngClass]="position.pnl >= 0 ? 'profit' : 'loss'">
          <span>PnL: {{ position.pnl | number:'1.2-2' }} ({{ position.pnl_pct | percent:'1.2-2' }})</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .position-ticker { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .no-position { color: var(--text-secondary); font-size: 12px; }
    .position-content { font-size: 12px; }
    .row { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .side { padding: 2px 6px; border-radius: 2px; font-size: 11px; }
    .buy { background: var(--accent-success, #26a69a); color: #fff; }
    .sell { background: var(--accent-danger, #ef5350); color: #fff; }
    .pnl { font-weight: 600; }
    .profit { color: var(--accent-success, #26a69a); }
    .loss { color: var(--accent-danger, #ef5350); }
  `],
})
export class PositionTickerComponent implements OnInit, OnDestroy {
  position: Position | null = null;
  private posSub?: Subscription;
  private posUpdateSub?: Subscription;

  constructor(
    private ws: ScalpingWsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Subscribe to position events from WS — updates in real-time
    this.posSub = this.ws.position$.subscribe((event: PositionEvent) => {
      this.position = {
        symbol: event.symbol,
        side: event.side,
        entry_price: event.entry_price,
        current_price: event.current_price,
        quantity: 0.001,
        pnl: event.pnl,
        pnl_pct: event.pnl_pct,
        leverage: 1,
        opened_at: new Date().toISOString()
      };
      this.cdr.detectChanges();
    });
  }

  ngOnDestroy(): void {
    this.posSub?.unsubscribe();
  }
}
