/**
 * Performance Panel Component
 * Displays win rate, profit factor, and trade statistics
 * Updated via WS trade_closed events instead of polling.
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
          <span class="pnl-values">
            <span class="value" [class.profit]="metrics.totalPnl >= 0" [class.loss]="metrics.totalPnl < 0">
              {{ metrics.totalPnl | number:'1.2-2' }} {{ quoteAsset }}
            </span>
            <span class="value pnl-pct" [class.profit]="metrics.totalPnl >= 0" [class.loss]="metrics.totalPnl < 0">
              {{ metrics.totalPnlPct | number:'1.2-2' }}%
            </span>
          </span>
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
      </div>
    </div>
  `,
  styles: [`
    .performance-panel { padding: 12px; }
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 10px 0 12px 0; }
    .no-data { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    .metrics-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
    .metric-item { display: flex; justify-content: space-between; padding: 10px 12px; background: var(--bg-elevated); border-radius: 6px; font-size: 14px; }
    .label { color: var(--text-secondary); }
    .value { font-weight: 600; color: var(--text-primary); }
    .value.profit { color: var(--accent-success, #26a69a); }
    .value.loss { color: var(--accent-danger, #ef5350); }
    .pnl-group { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: var(--bg-elevated); border-radius: 6px; font-size: 14px; }
    .pnl-values { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
    .pnl-pct { font-size: 12px; opacity: 0.8; }
    .warning { color: var(--accent-warning, #ffb74d); }
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

    // Refresh only when a trade closes — no polling, no initial load without session
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
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