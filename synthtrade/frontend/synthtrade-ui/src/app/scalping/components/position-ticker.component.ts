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
import { environment } from '../../../environments/environment.prod';

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
          <div class="target sl" [class.lock-active]="position.profit_lock_active" [class.trailing-active]="isTrailing()">
            <span class="target-label">
              Stop Loss
              <span *ngIf="position.profit_lock_active" class="lock-badge-small">🔒</span>
            </span>
            <span class="target-price">{{ position.stop_loss_price | number:'1.2-2' }}</span>
            <span class="target-pct">{{ formatSlPct() }}</span>
          </div>
          <div class="target tp">
            <span class="target-label">Take Profit</span>
            <span class="target-price">{{ position.take_profit_price | number:'1.2-2' }}</span>
            <span class="target-pct">{{ formatTpPct() }}</span>
          </div>
        </div>
        
        <!-- Progress Bar -->
        <div class="progress-container">
          <div class="progress-labels">
            <span class="label-sl">SL</span>
            <span class="label-current">{{ getProgressText() }}</span>
            <span class="label-tp">TP</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="getProgressPct()" [ngClass]="getProgressClass()"></div>
            <div class="entry-marker" [style.left.%]="getEntryPct()"></div>
            <!-- Marker breakeven: nascosto quando profit lock attivo (è già stato superato, non serve più) -->
            <div *ngIf="!position.profit_lock_active" class="breakeven-marker" [style.left.%]="getBreakevenPct()"></div>
          </div>
          <!-- Riga breakeven: sostituita da messaggio di allerta se profit lock attivo -->
          <div class="breakeven-row" *ngIf="!position.profit_lock_active">
            <span class="breakeven-tag">BE {{ getBreakevenPctValue() | number:'1.2-2' }}%</span>
            <span class="breakeven-status" [ngClass]="isAboveBreakeven() ? 'above' : 'below'">
              {{ isAboveBreakeven() ? '↑ Above Breakeven' : '↓ Below Breakeven' }}
            </span>
          </div>
          <div class="profit-lock-status" *ngIf="position.profit_lock_active && !isTrailing()">
            <span class="lock-status-icon">🔒</span>
            <span class="lock-status-text">Stop Loss Breakeven attivato — questo trade non può chiudersi in perdita.</span>
          </div>
          <div class="trailing-status" *ngIf="isTrailing()">
            <span class="lock-status-icon">🔒</span>
            <span class="lock-status-text">Trailing Stop attivo — Step {{ position.trailing_step }} · profitto protetto a {{ formatSlPct() }}</span>
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
      font-size: 13px;
      font-weight: 700;
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
      height: 20px;
      background: rgba(255,255,255,0.12);
      border-radius: 10px;
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
    .entry-marker {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 4px;
      background: rgba(255,255,255,0.45);
      transform: translateX(-2px);
      z-index: 2;
    }
    .breakeven-marker {
      position: absolute;
      top: -2px;
      width: 3px;
      height: 16px;
      background: #42A5F5;
      border-radius: 1px;
      transform: translateX(-1.5px);
      z-index: 3;
    }
    .breakeven-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
    }
    .breakeven-tag {
      white-space: nowrap;
      z-index: 2;
    }
    .breakeven-tag .be-text {
      font-size: 11px;
      font-weight: 700;
      color: #F0B90B;
      letter-spacing: 0.3px;
    }
    .breakeven-status {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }
    .breakeven-status.above {
      color: var(--accent-success, #26a69a);
    }
    .breakeven-status.below {
      color: var(--accent-danger, #ef5350);
    }
    .be-diff {
      font-weight: 400;
      text-transform: none;
      letter-spacing: 0;
    }

    /* TASK-1243: Profit Lock styles */
    .profit-lock-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      background: linear-gradient(90deg, rgba(240,185,11,0.15), rgba(240,185,11,0.06));
      border: 1px solid rgba(240,185,11,0.45);
      border-radius: 8px;
      padding: 8px 12px;
      animation: lockPulse 2s ease-in-out infinite;
    }
    .profit-lock-banner.trailing-active {
      background: linear-gradient(90deg, rgba(66,165,245,0.15), rgba(66,165,245,0.06));
      border-color: rgba(66,165,245,0.55);
    }
    .profit-lock-banner.trailing-active .lock-text {
      color: #42A5F5;
    }
    .profit-lock-banner.trailing-active .lock-sl {
      color: rgba(66,165,245,0.8);
    }
    @keyframes lockPulse {
      0%, 100% { border-color: rgba(240,185,11,0.45); }
      50%       { border-color: rgba(240,185,11,0.85); }
    }
    .lock-icon { font-size: 16px; }
    .lock-text {
      font-size: 11px;
      font-weight: 800;
      color: #F0B90B;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      flex: 1;
    }
    .lock-sl {
      font-size: 11px;
      font-weight: 700;
      color: rgba(240,185,11,0.8);
    }
    .target.lock-active {
      border-left-color: #F0B90B;
      background: rgba(240,185,11,0.06);
    }
    /* TASK-1247: trailing stop attivo (step >= 1) — tab SL verde */
    .target.sl.trailing-active {
      border-left-color: var(--accent-success, #26a69a);
      background: rgba(38,166,154,0.08);
    }
    .profit-lock-row {
      margin-top: 12px;
      padding: 8px 10px;
      background: rgba(240,185,11,0.08);
      border-radius: 6px;
      border: 1px solid rgba(240,185,11,0.25);
    }
    .lock-row-text {
      font-size: 11px;
      font-weight: 600;
      color: #F0B90B;
      line-height: 1.4;
    }
    /* fallback per il vecchio profit-lock-status se presente */
    .profit-lock-status {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 12px;
      padding: 7px 10px;
      background: rgba(240,185,11,0.08);
      border-radius: 6px;
      border: 1px solid rgba(240,185,11,0.25);
    }
    .lock-status-icon { font-size: 14px; }
    .lock-status-text {
      font-size: 11px;
      font-weight: 600;
      color: #F0B90B;
      line-height: 1.4;
    }
    /* TASK-1247: stato trailing attivo — messaggio verde */
    .trailing-status {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 12px;
      padding: 7px 10px;
      background: rgba(38,166,154,0.1);
      border-radius: 6px;
      border: 1px solid rgba(38,166,154,0.35);
    }
    .trailing-status .lock-status-icon { font-size: 14px; }
    .trailing-status .lock-status-text {
      font-size: 11px;
      font-weight: 600;
      color: #26a69a;
      line-height: 1.4;
    }
  `],
})
export class PositionTickerComponent implements OnInit, OnDestroy {
  position: Position | null = null;
  quoteAsset: string = 'USDT';
  private posSub?: Subscription;
  private posUpdateSub?: Subscription;
  private readonly POSITION_API = environment.apiUrl + '/scalping/position';

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
        stop_loss_pct_net: event.stop_loss_pct_net,
        take_profit_pct_net: event.take_profit_pct_net,
        trade_value_usd: event.trade_value_usd ?? (event.quantity ? event.quantity * event.entry_price : undefined),
        breakeven_pct: event.breakeven_pct,
        // TASK-1243: profit lock
        profit_lock_active: event.profit_lock_active ?? this.position?.profit_lock_active ?? false,
        profit_lock_sl_price: event.profit_lock_sl_price ?? this.position?.profit_lock_sl_price,
        // TASK-1246: trailing step
        trailing_step: event.trailing_step ?? this.position?.trailing_step ?? 0,
        // TASK-1247: SL net % effettivo (post amend break-even/trailing)
        sl_net_pct: event.sl_net_pct ?? this.position?.sl_net_pct,
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
      stop_loss_price?: number;
      take_profit_price?: number;
      stop_loss_pct?: number;
      take_profit_pct?: number;
      stop_loss_pct_net?: number;
      take_profit_pct_net?: number;
      breakeven_pct?: number;
      profit_lock_active?: boolean;
      trailing_step?: number;
      sl_net_pct?: number;
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
            stop_loss_price: pos.stop_loss_price ?? pos.entry_price * 0.997,
            take_profit_price: pos.take_profit_price ?? pos.entry_price * 1.005,
            stop_loss_pct: pos.stop_loss_pct ?? -0.3,
            take_profit_pct: pos.take_profit_pct ?? 0.5,
            stop_loss_pct_net: pos.stop_loss_pct_net,
            take_profit_pct_net: pos.take_profit_pct_net,
            breakeven_pct: pos.breakeven_pct,
            profit_lock_active: pos.profit_lock_active ?? false,
            trailing_step: pos.trailing_step ?? 0,
            sl_net_pct: pos.sl_net_pct,
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

  /** True quando il trailing stop è attivo (almeno uno step applicato). */
  isTrailing(): boolean {
    return (this.position?.trailing_step ?? 0) >= 1;
  }

  /**
   * Percentuale SL con segno. Usa il valore netto effettivo al prezzo SL corrente
   * (sl_net_pct, ricalcolato dal backend dopo break-even/trailing); fallback al
   * target netto di config come valore negativo (es. -0.30%).
   */
  formatSlPct(): string {
    const p = this.position;
    if (!p) return '';
    let val: number;
    if (p.sl_net_pct !== undefined && p.sl_net_pct !== null) {
      val = p.sl_net_pct;
    } else {
      const cfg = p.stop_loss_pct_net ?? p.stop_loss_pct ?? 0;
      val = cfg >= 0 ? -cfg : cfg;
    }
    return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
  }

  /** Percentuale TP con segno + (es. +0.80%). */
  formatTpPct(): string {
    const p = this.position;
    if (!p) return '';
    const val = p.take_profit_pct_net ?? p.take_profit_pct ?? 0;
    return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
  }

  getProgressPct(): number {
    if (!this.position) return 0;
    const { side, current_price, stop_loss_price, take_profit_price } = this.position;
    if (!stop_loss_price || !take_profit_price) return 0;

    if (side === 'BUY') {
      const range = take_profit_price - stop_loss_price;
      if (range <= 0) return 0;
      return Math.max(0, Math.min(100, ((current_price - stop_loss_price) / range) * 100));
    }
    const range = stop_loss_price - take_profit_price;
    if (range <= 0) return 0;
    return Math.max(0, Math.min(100, ((stop_loss_price - current_price) / range) * 100));
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
   * Breakeven position on the progress bar (0-100%).
   * The breakeven price = entry + (entry * breakeven_pct / 100) for BUY.
   * Maps that price onto the SL→TP range.
   */
  getBreakevenPct(): number {
    if (!this.position) return 50;
    const { side, entry_price, stop_loss_price, take_profit_price, breakeven_pct } = this.position;
    if (!stop_loss_price || !take_profit_price) return 50;

    const bePct = breakeven_pct ?? 0.2;
    if (side === 'BUY') {
      const bePrice = entry_price * (1 + bePct / 100);
      const range = take_profit_price - stop_loss_price;
      if (range <= 0) return 50;
      return Math.max(0, Math.min(100, ((bePrice - stop_loss_price) / range) * 100));
    }
    const bePrice = entry_price * (1 - bePct / 100);
    const range = stop_loss_price - take_profit_price;
    if (range <= 0) return 50;
    return Math.max(0, Math.min(100, ((stop_loss_price - bePrice) / range) * 100));
  }

  /** Entry position on the progress bar (0-100%) */
  getEntryPct(): number {
    if (!this.position) return 50;
    const { side, entry_price, stop_loss_price, take_profit_price } = this.position;
    if (!stop_loss_price || !take_profit_price) return 50;

    if (side === 'BUY') {
      const range = take_profit_price - stop_loss_price;
      if (range <= 0) return 50;
      return Math.max(0, Math.min(100, ((entry_price - stop_loss_price) / range) * 100));
    }
    const range = stop_loss_price - take_profit_price;
    if (range <= 0) return 50;
    return Math.max(0, Math.min(100, ((stop_loss_price - entry_price) / range) * 100));
  }

  /** Breakeven price (entry + round-trip fees) */
  getBreakevenPrice(): number {
    if (!this.position) return 0;
    const { side, entry_price, breakeven_pct } = this.position;
    const bePct = breakeven_pct ?? 0.2;
    return side === 'BUY'
      ? entry_price * (1 + bePct / 100)
      : entry_price * (1 - bePct / 100);
  }

  /** Raw breakeven percentage value (for display) */
  getBreakevenPctValue(): number {
    return this.position?.breakeven_pct ?? 0.2;
  }

  /** Is current price above breakeven? */
  isAboveBreakeven(): boolean {
    if (!this.position) return false;
    const { side, current_price } = this.position;
    const bePrice = this.getBreakevenPrice();
    return side === 'BUY' ? current_price >= bePrice : current_price <= bePrice;
  }

  /** Difference between current price and breakeven in % */
  getBreakevenDiff(): number {
    if (!this.position) return 0;
    const { side, current_price, entry_price } = this.position;
    const bePrice = this.getBreakevenPrice();
    if (entry_price === 0) return 0;
    return side === 'BUY'
      ? ((current_price - bePrice) / entry_price) * 100
      : ((bePrice - current_price) / entry_price) * 100;
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
