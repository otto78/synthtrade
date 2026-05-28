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

@Component({
  selector: 'app-performance-panel',
  standalone: true,
  imports: [DecimalPipe, PercentPipe, NgIf],
  template: `
    <div class="performance-panel">
      <h3>Performance</h3>

      <div *ngIf="!metrics" class="loading">Loading...</div>

      <div *ngIf="metrics" class="metrics-grid">
        <div class="metric-item">
          <span class="label">Total PnL</span>
          <span class="value" [class.profit]="metrics.totalPnl >= 0" [class.loss]="metrics.totalPnl < 0">
            {{ metrics.totalPnl | number:'1.2-2' }} USDT
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
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .loading { color: var(--text-secondary); font-size: 12px; }
    .metrics-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
    .metric-item { display: flex; justify-content: space-between; padding: 10px 12px; background: var(--bg-elevated); border-radius: 6px; font-size: 14px; }
    .label { color: var(--text-secondary); }
    .value { font-weight: 600; color: var(--text-primary); }
    .value.profit { color: var(--accent-success, #26a69a); }
    .value.loss { color: var(--accent-danger, #ef5350); }
    .warning { color: var(--accent-warning, #ffb74d); }
  `],
})
export class PerformancePanelComponent implements OnInit, OnDestroy {
  metrics?: PerformanceMetrics;
  private sub?: Subscription;

  constructor(
    private perfApi: PerformanceApiService,
    private ws: ScalpingWsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadMetrics();
    // Refresh only when a trade closes — no polling
    this.sub = this.ws.tradeClosed$.subscribe(() => this.loadMetrics());
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  private loadMetrics(): void {
    this.perfApi.getMetrics().subscribe({
      next: (data) => {
        this.metrics = data;
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }
}