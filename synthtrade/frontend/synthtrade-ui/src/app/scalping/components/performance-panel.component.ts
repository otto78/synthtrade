/**
 * Performance Panel Component
 * Displays win rate, profit factor, and trade statistics
 * Updated via WS trade_closed events instead of polling.
 * Includes Trading vs Hold comparison widget.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { DecimalPipe, PercentPipe, NgIf } from '@angular/common';
import { Subscription } from 'rxjs';
import { PerformanceApiService, PerformanceMetrics } from '../services/performance-api.service';
import { ScalpingWsService } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';

@Component({
  selector: 'app-performance-panel',
  standalone: true,
  imports: [DecimalPipe, PercentPipe, NgIf],
  template: `
    <div class="performance-panel">
      <span class="panel-title">Performance</span>
      <div class="title-hr"></div>

      <div *ngIf="!metrics" class="no-data">No performance yet</div>

      <div *ngIf="metrics" class="metrics-grid">
        <div class="metric-item pnl-group">
          <span class="label">Total PnL</span>
          <div class="pnl-values">
            <span class="pnl-main" [class.profit]="metrics.totalPnl >= 0" [class.loss]="metrics.totalPnl < 0">
              {{ metrics.totalPnl >= 0 ? '+' : '' }}{{ metrics.totalPnl | number:'1.2-2' }} {{ quoteAsset }}
            </span>
            <span class="pnl-pct" [class.profit]="metrics.totalPnl >= 0" [class.loss]="metrics.totalPnl < 0">
              {{ metrics.totalPnlPct >= 0 ? '+' : '' }}{{ metrics.totalPnlPct | number:'1.2-2' }}%
            </span>
          </div>
        </div>

        <!-- Trading vs Hold comparison -->
        <div class="metric-item hold-compare" *ngIf="metrics.holdPnlPct !== null">
          <div class="hold-header">
            <span class="label">vs Hold</span>
            <span class="hold-badge" [class.winning]="metrics.tradingBeatsHold === true" [class.losing]="metrics.tradingBeatsHold === false">
              {{ metrics.tradingBeatsHold === true ? '▲ Batti il Hold' : metrics.tradingBeatsHold === false ? '▼ Hold ti batte' : '—' }}
            </span>
          </div>
          <div class="hold-bars">
            <div class="hold-bar-row">
              <span class="bar-label">Trading</span>
              <div class="bar-track">
                <div class="bar-fill trading" [style.width.%]="getTradingBarPct()" [class.profit]="metrics.totalPnlPct >= 0" [class.loss]="metrics.totalPnlPct < 0"></div>
              </div>
              <span class="bar-val" [class.profit]="metrics.totalPnlPct >= 0" [class.loss]="metrics.totalPnlPct < 0">{{ metrics.totalPnlPct | number:'1.2-2' }}%</span>
            </div>
              <div class="hold-bar-row">
              <span class="bar-label">Hold</span>
              <div class="bar-track">
                <div class="bar-fill hold"
                  [style.width.%]="getHoldBarPct()"
                  [class.profit]="(metrics.holdPnlPct || 0) >= 0"
                  [class.loss]="(metrics.holdPnlPct || 0) < 0">
                </div>
              </div>
              <span class="bar-val"
                [class.profit]="(metrics.holdPnlPct || 0) >= 0"
                [class.loss]="(metrics.holdPnlPct || 0) < 0">{{ metrics.holdPnlPct | number:'1.2-2' }}%</span>
            </div>
          </div>
        </div>

        <div class="metric-item">
          <span class="label">Win Rate</span>
          <span class="value">{{ metrics.winRate | percent:'1.1-1' }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Total Trades</span>
          <span class="value">{{ metrics.totalTrades }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Profit Factor</span>
          <span class="value">{{ metrics.profitFactor | number:'1.2-2' }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Avg Win</span>
          <span class="value profit">{{ metrics.avgWin | number:'1.2-2' }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Avg Loss</span>
          <span class="value loss">{{ metrics.avgLoss | number:'1.2-2' }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Max Drawdown</span>
          <span class="value">{{ metrics.maxDrawdown | percent:'1.1-1' }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Consecutive Losses</span>
          <span class="value" [class.warning]="metrics.consecutiveLosses >= 3">{{ metrics.consecutiveLosses }}</span>
        </div>
        <div class="metric-item">
          <span class="label">Wins / Losses</span>
          <span class="value"
            [class.profit]="metrics.winningTrades > metrics.losingTrades"
            [class.loss]="metrics.losingTrades > metrics.winningTrades">
            {{ metrics.winningTrades }} / {{ metrics.losingTrades }}
          </span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .performance-panel { padding: 12px; }
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 10px 0 12px 0; }
    .no-data { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .metric-item { display: flex; justify-content: space-between; padding: 10px 12px; background: var(--bg-elevated); border-radius: 6px; font-size: 14px; }
    .label { color: var(--text-secondary); }
    .value { font-weight: 600; color: var(--text-primary); }
    .value.profit { color: var(--accent-success, #26a69a); }
    .value.loss { color: var(--accent-danger, #ef5350); }
    .pnl-group { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: var(--bg-elevated); border-radius: 6px; grid-column: span 2; }
    .pnl-values { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
    .pnl-main { font-size: 20px; font-weight: 700; line-height: 1.1; }
    .pnl-main.profit { color: var(--accent-success, #26a69a); }
    .pnl-main.loss { color: var(--accent-danger, #ef5350); }
    .pnl-pct { font-size: 12px; opacity: 0.75; font-weight: 600; }
    .pnl-pct.profit { color: var(--accent-success, #26a69a); }
    .pnl-pct.loss { color: var(--accent-danger, #ef5350); }
    .hold-compare { flex-direction: column; gap: 8px; background: rgba(240,185,11,0.04); border: 1px solid rgba(240,185,11,0.12); grid-column: span 2; }
    .hold-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
    }
    .hold-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 20px;
      letter-spacing: 0.3px;
    }
    .hold-badge.winning {
      background: rgba(38,166,154,0.15);
      color: #26a69a;
      border: 1px solid rgba(38,166,154,0.3);
    }
    .hold-badge.losing {
      background: rgba(239,83,80,0.12);
      color: #ef5350;
      border: 1px solid rgba(239,83,80,0.25);
    }
    .hold-bars { display: flex; flex-direction: column; gap: 6px; width: 100%; }
    .hold-bar-row { display: flex; align-items: center; gap: 6px; }
    .bar-label { font-size: 10px; color: var(--text-secondary); width: 44px; flex-shrink: 0; }
    .bar-track { flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; min-width: 2px; }
    .bar-fill.trading.profit { background: linear-gradient(90deg, #26a69a, #4db6ac); }
    .bar-fill.trading.loss  { background: linear-gradient(90deg, #ef5350, #ff6b6b); }
    .bar-fill.hold.profit   { background: rgba(38,166,154,0.4); }
    .bar-fill.hold.loss     { background: rgba(239,83,80,0.4); }
    .bar-val { font-size: 11px; font-weight: 700; width: 48px; text-align: right; flex-shrink: 0; }
    .bar-val.profit { color: #26a69a; }
    .bar-val.loss   { color: #ef5350; }
  `],
})
export class PerformancePanelComponent implements OnInit, OnDestroy {
  metrics?: PerformanceMetrics;
  quoteAsset: string = 'USDT';
  private sub?: Subscription;

  constructor(
    private perfApi: PerformanceApiService,
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Reset metrics when a new session starts
    this.sub = this.sessionApi.session$.subscribe((session) => {
      if (!session || session.status === 'idle') {
        this.metrics = undefined;
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      } else if (session.status === 'running') {
        this.metrics = undefined;
        this.cdr.markForCheck();
        this.cdr.detectChanges();
        // Update quote asset from session symbol
        if (session.symbol) {
          const sym = session.symbol.toUpperCase();
          if (sym.endsWith('USDC')) this.quoteAsset = 'USDC';
          else if (sym.endsWith('EUR')) this.quoteAsset = 'EUR';
          else this.quoteAsset = 'USDT';
        }
        this.loadMetrics();
      }
    });

    // Refresh only when a trade closes — no polling
    this.sub.add(this.ws.tradeClosed$.subscribe(() => this.loadMetrics()));
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  /** Normalize trading pct to a bar width (max 100%) */
  getTradingBarPct(): number {
    if (!this.metrics) return 0;
    const maxAbs = Math.max(Math.abs(this.metrics.totalPnlPct), Math.abs(this.metrics.holdPnlPct ?? 0), 0.01);
    return Math.min(100, (Math.abs(this.metrics.totalPnlPct) / maxAbs) * 100);
  }

  /** Normalize hold pct to a bar width (max 100%) */
  getHoldBarPct(): number {
    if (!this.metrics || this.metrics.holdPnlPct === null) return 0;
    const maxAbs = Math.max(Math.abs(this.metrics.totalPnlPct), Math.abs(this.metrics.holdPnlPct ?? 0), 0.01);
    return Math.min(100, (Math.abs(this.metrics.holdPnlPct ?? 0) / maxAbs) * 100);
  }

  private loadMetrics(): void {
    this.perfApi.getMetrics().subscribe({
      next: (data) => {
        this.metrics = data;
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }
}