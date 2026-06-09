/**
 * Position Ticker Component
 * Shows open position from WS events (candle, position updates).
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { NgIf, NgClass, DecimalPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { ScalpingWsService, PositionEvent } from '../services/scalping-ws.service';
import { Position } from '../models/position.model';

@Component({
  selector: 'app-position-ticker',
  standalone: true,
  imports: [NgIf, NgClass, DecimalPipe],
  template: `
    <div class="position-ticker">
      <span class="panel-title">Position</span>

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
          <span class="pnl-value">PnL: {{ position.pnl | number:'1.2-2' }} USDT</span>
          <span class="pnl-pct">{{ position.pnl_pct | number:'1.2-2' }}%</span>
        </div>
        
        <!-- Exit Targets -->
        <div class="exit-targets">
          <div class="target sl">
            <span class="target-label">Stop Loss</span>
            <span class="target-price">{{ position.stop_loss_price | number:'1.2-2' }}</span>
            <span class="target-pct">({{ position.stop_loss_pct | number:'1.2-2' }}%)</span>
          </div>
          <div class="target tp">
            <span class="target-label">Take Profit</span>
            <span class="target-price">{{ position.take_profit_price | number:'1.2-2' }}</span>
            <span class="target-pct">(+{{ position.take_profit_pct | number:'1.2-2' }}%)</span>
          </div>
        </div>
        
        <!-- Progress Bar -->
        <div class="progress-container">
          <div class="progress-labels">
            <span class="label-sl">SL</span>
            <span class="label-current">{{ position.pnl_pct | number:'1.1-1' }}%</span>
            <span class="label-tp">TP</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="getProgressPct()" [ngClass]="getProgressClass()"></div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .position-ticker { padding: 12px; }
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .no-position { color: var(--text-secondary); font-size: 12px; }
    .position-content { font-size: 12px; display: flex; flex-direction: column; gap: 10px; }
    .row { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .side { padding: 2px 6px; border-radius: 2px; font-size: 11px; }
    .buy { background: var(--accent-success, #26a69a); color: #fff; }
    .sell { background: var(--accent-danger, #ef5350); color: #fff; }
    .pnl { font-weight: 600; display: flex; justify-content: space-between; }
    .profit { color: var(--accent-success, #26a69a); }
    .loss { color: var(--accent-danger, #ef5350); }
    .pnl-value { flex: 1; }
    .pnl-pct { font-size: 13px; font-weight: 700; }
    
    /* Exit Targets */
    .exit-targets {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 6px;
      padding-top: 8px;
      border-top: 1px solid rgba(255,255,255,0.06);
    }
    .target {
      background: rgba(255,255,255,0.03);
      border-radius: 6px;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .target.sl {
      border-left: 2px solid var(--accent-danger, #ef5350);
    }
    .target.tp {
      border-left: 2px solid var(--accent-success, #26a69a);
    }
    .target-label {
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
      font-weight: 600;
    }
    .target-price {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .target-pct {
      font-size: 10px;
      color: var(--text-secondary);
    }
    
    /* Progress Bar */
    .progress-container {
      margin-top: 8px;
    }
    .progress-labels {
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      margin-bottom: 4px;
    }
    .label-sl { color: var(--accent-danger, #ef5350); font-weight: 600; }
    .label-current { color: var(--text-primary); font-weight: 700; }
    .label-tp { color: var(--accent-success, #26a69a); font-weight: 600; }
    .progress-bar {
      height: 8px;
      background: rgba(255,255,255,0.08);
      border-radius: 4px;
      overflow: hidden;
      position: relative;
    }
    .progress-fill {
      height: 100%;
      transition: width 0.3s ease, background-color 0.3s ease;
      border-radius: 4px;
    }
    .progress-fill.danger {
      background: linear-gradient(90deg, #ef5350, #ff6b6b);
    }
    .progress-fill.warning {
      background: linear-gradient(90deg, #ffb74d, #ffa726);
    }
    .progress-fill.success {
      background: linear-gradient(90deg, #26a69a, #4db6ac);
    }
  `],
})
export class PositionTickerComponent implements OnInit, OnDestroy {
  position: Position | null = null;
  private posSub?: Subscription;
  private posUpdateSub?: Subscription;
  private readonly POSITION_API = '/api/scalping/position';

  constructor(
    private ws: ScalpingWsService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Step 1: Fetch open position from REST API (for page refresh recovery)
    this.loadInitialPosition();

    // Step 2: Subscribe to position events from WS — updates in real-time
    this.posSub = this.ws.position$.pipe(
      filter(event => event !== null)
    ).subscribe((event: PositionEvent) => {
      this.position = {
        symbol: event.symbol,
        side: event.side,
        entry_price: event.entry_price,
        current_price: event.current_price,
        quantity: 0.001,
        pnl: event.pnl,
        pnl_pct: event.pnl_pct,
        leverage: 1,
        opened_at: new Date().toISOString(),
        stop_loss_price: event.stop_loss_price,
        take_profit_price: event.take_profit_price,
        stop_loss_pct: event.stop_loss_pct,
        take_profit_pct: event.take_profit_pct,
      };
      this.cdr.markForCheck();
      this.cdr.detectChanges();
    });
    
    // Clear position when a trade is closed
    this.posUpdateSub = this.ws.tradeClosed$.subscribe(() => {
      this.position = null;
      this.cdr.markForCheck();
      this.cdr.detectChanges();
    });
  }

  private loadInitialPosition(): void {
    interface PositionApiResponse {
      symbol: string;
      side: string;
      entry_price: number;
      current_price: number;
      quantity: number;
      pnl: number;
      pnl_pct: number;
      entry_time: string;
      status?: string;
    }
    this.http.get<PositionApiResponse | null>(this.POSITION_API).subscribe({
      next: (pos) => {
        if (pos) {
          const side = pos.side === 'BUY' ? 'BUY' as const : 'SELL' as const;
          this.position = {
            symbol: pos.symbol,
            side: side,
            entry_price: pos.entry_price,
            current_price: pos.current_price,
            quantity: pos.quantity,
            pnl: pos.pnl,
            pnl_pct: pos.pnl_pct,
            leverage: 1,
            opened_at: pos.entry_time,
            stop_loss_price: pos.entry_price * 0.997,
            take_profit_price: pos.entry_price * 1.005,
            stop_loss_pct: -0.3,
            take_profit_pct: 0.5,
          };
          this.cdr.markForCheck();
          this.cdr.detectChanges();
          console.log(`[PositionTicker] Restored open position: ${pos.side} ${pos.symbol} @ ${pos.entry_price}`);
        }
      },
      error: () => {} // Silently fail — position will appear via WS when live
    });
  }
  
  getProgressPct(): number {
    if (!this.position) return 0;
    const tpPct = this.position.take_profit_pct ?? 0;
    const slPct = this.position.stop_loss_pct ?? 0;
    const range = tpPct - slPct;
    const current = this.position.pnl_pct - slPct;
    return Math.max(0, Math.min(100, (current / range) * 100));
  }
  
  getProgressClass(): string {
    const progress = this.getProgressPct();
    if (progress < 30) return 'danger';
    if (progress < 70) return 'warning';
    return 'success';
  }

  ngOnDestroy(): void {
    this.posSub?.unsubscribe();
    this.posUpdateSub?.unsubscribe();
  }
}
