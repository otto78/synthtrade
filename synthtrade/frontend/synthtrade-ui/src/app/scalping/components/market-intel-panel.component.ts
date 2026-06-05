/**
 * Market Intelligence Panel Component
 * Displays real-time market data: funding rate, OI, CVD, Fear&Greed, Signal Score.
 * Listens to symbol changes from active session.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { UpperCasePipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { IntelligenceApiService } from '../services/intelligence-api.service';
import { MarketIntelSnapshot } from '../models/intelligence.model';
import { ScalpingWsService, IntelligenceEvent } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';

@Component({
  selector: 'app-market-intel-panel',
  standalone: true,
  imports: [UpperCasePipe],
  template: `
    <div class="intel-panel">
      <h3>Market Intelligence <span class="sym-badge">{{ symbol }}</span></h3>
      <div class="intel-grid">
        <div class="intel-item">
          <span class="label">Signal Score</span>
          <span class="value score" [class.bullish]="signalBias === 'bullish'" [class.bearish]="signalBias === 'bearish'">
            {{ signalScore }}
          </span>
        </div>
        <div class="intel-item">
          <span class="label">Bias</span>
          <span class="value" [class.bullish]="signalBias === 'bullish'" [class.bearish]="signalBias === 'bearish'">
            {{ signalBias | uppercase }}
          </span>
        </div>
        <div class="intel-item">
          <span class="label">Funding Rate</span>
          <span class="value" [class.cold]="fundingRateNum < 0" [class.hot]="fundingRateNum > 0">
            {{ fundingRate }}
          </span>
        </div>
        <div class="intel-item">
          <span class="label">Fear & Greed</span>
          <span class="value">{{ fearGreed }}</span>
        </div>
        <div class="intel-item">
          <span class="label">Open Interest</span>
          <span class="value">{{ openInterest }}</span>
        </div>
        <div class="intel-item">
          <span class="label">CVD Trend</span>
          <span class="value" [class.bullish]="cvdTrend === 'rising'" [class.bearish]="cvdTrend === 'falling'">
            {{ cvdTrend | uppercase }}
          </span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .intel-panel { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .sym-badge { font-size: 11px; color: var(--accent-primary, #F0B90B); background: rgba(240,185,11,0.1); padding: 1px 6px; border-radius: 4px; font-weight: 600; }
    .intel-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
    .intel-item { display: flex; justify-content: space-between; padding: 10px 12px; background: var(--bg-elevated); border-radius: 6px; }
    .label { font-size: 13px; color: var(--text-secondary); }
    .value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
    .value.score { font-size: 18px; }
    .value.bullish { color: var(--color-buy, #0ECB81); }
    .value.bearish { color: var(--color-sell, #F6465D); }
    .value.hot { color: var(--color-buy, #0ECB81); }
    .value.cold { color: var(--color-sell, #F6465D); }
  `],
})
export class MarketIntelPanelComponent implements OnInit, OnDestroy {
  fundingRate = '--';
  fundingRateNum = 0;
  openInterest = '--';
  fearGreed = '--';
  signalScore = '--';
  signalBias: 'bullish' | 'bearish' | 'neutral' = 'neutral';
  cvdTrend = '--';

  /** Symbol shown in template — updated from active session */
  symbol: string = 'BTCUSDT';
  private sub = new Subscription();

  constructor(
    private intelApi: IntelligenceApiService,
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Sync symbol from active session
    this.sub.add(
      this.sessionApi.session$.subscribe((session) => {
        if (session && session.symbol && session.status !== 'idle') {
          if (session.symbol !== this.symbol) {
            this.symbol = session.symbol;
            this.loadSnapshot();
          }
        }
      })
    );

    // Load initial snapshot
    this.loadSnapshot();
    
    // Listen to real-time updates from WebSocket
    this.sub.add(
      this.ws.intelligence$.subscribe((data: IntelligenceEvent | null) => {
        if (!data) return;
        // If WS event has a symbol and it's ours — update
        if (data.symbol && data.symbol.toUpperCase() !== this.symbol.toUpperCase()) {
          return; // skip events for other symbols
        }
        if (data.signal_score !== undefined) {
          this.signalScore = data.signal_score.toFixed(1);
        }
        if (data.signal_bias) {
          this.signalBias = data.signal_bias;
        }
        if (data.funding_rate !== undefined) {
          this.fundingRate = data.funding_rate.toFixed(4);
          this.fundingRateNum = data.funding_rate;
        }
        if (data.fear_greed_label) {
          this.fearGreed = data.fear_greed_label;
        }
        if (data.open_interest !== undefined) {
          this.openInterest = this.formatLargeNumber(data.open_interest);
        }
        if (data.cvd_trend) {
          this.cvdTrend = data.cvd_trend;
        }
        this.cdr.detectChanges();
      })
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  private loadSnapshot(): void {
    this.intelApi.getLatestSnapshot(this.symbol).subscribe({
      next: (data: MarketIntelSnapshot) => {
        if (data.signal_score !== undefined) {
          this.signalScore = data.signal_score.toFixed(1);
        }
        if (data.signal_bias) {
          this.signalBias = data.signal_bias;
        }
        if (data.funding_rate !== undefined) {
          this.fundingRate = data.funding_rate.toFixed(4);
          this.fundingRateNum = data.funding_rate;
        }
        if (data.fear_greed_label) {
          this.fearGreed = data.fear_greed_label;
        }
        if (data.open_interest !== undefined) {
          this.openInterest = this.formatLargeNumber(data.open_interest);
        }
        if (data.cvd_trend) {
          this.cvdTrend = data.cvd_trend;
        }
      },
      error: (err: Error) => {
        console.error('Intelligence load error:', err);
      }
    });
  }

  private formatLargeNumber(num: number): string {
    if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(2) + 'B';
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(2) + 'K';
    return num.toFixed(0);
  }
}