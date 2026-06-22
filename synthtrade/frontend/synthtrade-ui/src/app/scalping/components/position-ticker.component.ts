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
import { SessionApiService } from '../services/session-api.service';
import { Position } from '../models/position.model';

@Component({
  selector: 'app-position-ticker',
  standalone: true,
  imports: [NgIf, NgClass, DecimalPipe],
  template: `
    <div class="position-ticker">
      <span class="panel-title">Position</span>
      <div class="title-hr"></div>

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
          <span>Date: {{ formatEntryTime() }}</span>
        </div>

        <!-- Trade value (gross amount) -->
        <div class="row invested" *ngIf="getTradeValue()">
          <span class="inv-label">Valore Trade</span>
          <span class="inv-value">{{ getTradeValue() | number:'1.2-2' }} {{ quoteAsset }}</span>
        </div>

        <div class="row pnl" [ngClass]="position.pnl >= 0 ? 'profit' : 'loss'">
          <span class="pnl-value">PnL: {{ position.pnl | number:'1.2-2' }} {{ quoteAsset }}</span>
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
          <div class="progress-state" [ngClass]="getProgressClass()">{{ getProgressText() }}</div>
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
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 10px 0 12px 0; }
    .no-position { color: var(--text-secondary); font-size: 12px; }
    .position-content { font-size: 12px; display: flex; flex-direction: column; gap: 10px; }
    .row { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .side { padding: 2px 6px; border-radius: 2px; font-size: 11px; }
    .buy { background: var(--accent-success, #26a69a); color: #fff; }
    .sell { background: var(--accent-danger, #ef5350); color: #fff; }
    .invested { 
      background: rgba(240,185,11,0.06); 
      border: 1px solid rgba(240,185,11,0.15); 
      border-radius: 6px; 
      padding: 6px 10px;
      margin-bottom: 2px;
    }
    .inv-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); }
    .inv-value { font-size: 13px; font-weight: 700; color: #F0B90B; }
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
      height: 10px;
      background: rgba(255,255,255,0.12);
      border-radius: 5px;
      overflow: hidden;
      position: relative;
    }
    .progress-state {
      font-size: 11px;
      font-weight: 700;
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }
    .progress-fill {
      height: 100%;
      transition: width 0.3s ease, background-color 0.3s ease;
      border-radius: 5px;
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
  quoteAsset: string = 'USDT';
  private posSub?: Subscription;
  private posUpdateSub?: Subscription;
  private readonly POSITION_API = '/api/scalping/position';

  private _updateQuoteAsset(symbol: string): void {
    if (symbol.endsWith('USDC')) this.quoteAsset = 'USDC';
    else if (symbol.endsWith('EUR')) this.quoteAsset = 'EUR';
    else this.quoteAsset = 'USDT';
  }

  constructor(
    private ws: ScalpingWsService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private sessionApi: SessionApiService
  ) {}

  ngOnInit(): void {
    // Step 1: Fetch open position from REST API (for page refresh recovery)
    this.loadInitialPosition();

    // Step 2: Subscribe to position events from WS — updates in real-time
    this.posSub = this.ws.position$.pipe(
      filter(event => event !== null)
    ).subscribe((event: PositionEvent) => {
      this._updateQuoteAsset(event.symbol);
      // Preserve existing entry_time/opened_at if the event doesn't carry it
      // (position_update events only update PnL/price, not entry metadata)
      const existingEntryTime = this.position?.entry_time || this.position?.opened_at;
      this.position = {
        symbol: event.symbol,
        side: event.side,
        entry_price: event.entry_price,
        current_price: event.current_price,
        entry_time: event.entry_time || existingEntryTime,
        quantity: event.quantity ?? 0,
        pnl: event.pnl,
        pnl_pct: event.pnl_pct,
        leverage: 1,
        opened_at: existingEntryTime || new Date().toISOString(),
        stop_loss_price: event.stop_loss_price,
        take_profit_price: event.take_profit_price,
        stop_loss_pct: event.stop_loss_pct,
        take_profit_pct: event.take_profit_pct,
        trade_value_usd: event.trade_value_usd ?? (event.quantity ? event.quantity * event.entry_price : undefined),
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
          this._updateQuoteAsset(pos.symbol);
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
  
  /**
   * Returns the trade value from the session config (the exact amount set by user, e.g. 20 USDC).
   * Fallback to quantity × entry_price if session not yet loaded.
   */
  getTradeValue(): number {
    const session = this.sessionApi.getActiveSession();
    if (session?.trade_value) return session.trade_value;
    if (!this.position) return 0;
    return this.position.quantity * this.position.entry_price;
  }

  getProgressPct(): number {
    if (!this.position) return 0;
    const { side, current_price, stop_loss_price, take_profit_price } = this.position;
    if (stop_loss_price == null || take_profit_price == null) return 0;

    if (side === 'BUY') {
      const totalRange = take_profit_price - stop_loss_price;
      if (totalRange <= 0) return 0;
      const progress = ((current_price - stop_loss_price) / totalRange) * 100;
      return Math.max(0, Math.min(100, progress));
    }

    const totalRange = stop_loss_price - take_profit_price;
    if (totalRange <= 0) return 0;
    const progress = ((stop_loss_price - current_price) / totalRange) * 100;
    return Math.max(0, Math.min(100, progress));
  }

  getProgressText(): string {
    const progress = this.getProgressPct();
    if (progress <= 10) return 'Near SL';
    if (progress >= 90) return 'Near TP';
    return 'In range';
  }

  getProgressClass(): string {
    const progress = this.getProgressPct();
    if (progress < 30) return 'danger';
    if (progress < 70) return 'warning';
    return 'success';
  }

  /**
   * Format entry_time for display. Shows short time + date (e.g. "14:32 20/06")
   * Falls back to opened_at if entry_time is not available.
   */
  formatEntryTime(): string {
    const ts = this.position?.entry_time || this.position?.opened_at;
    if (!ts) return '--';
    try {
      const d = new Date(ts);
      const h = d.getHours().toString().padStart(2, '0');
      const m = d.getMinutes().toString().padStart(2, '0');
      const day = d.getDate().toString().padStart(2, '0');
      const month = (d.getMonth() + 1).toString().padStart(2, '0');
      return `${h}:${m} ${day}/${month}`;
    } catch {
      return ts.slice(0, 16);
    }
  }

  ngOnDestroy(): void {
    this.posSub?.unsubscribe();
    this.posUpdateSub?.unsubscribe();
  }
}
