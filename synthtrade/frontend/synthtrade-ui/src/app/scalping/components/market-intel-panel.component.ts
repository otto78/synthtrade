/**
 * Market Intelligence Panel Component
 * Displays real-time market data: funding rate, OI, CVD, Fear&Greed, Signal Score.
 * Listens to symbol changes from active session.
 * Shows signal score vs current threshold for quick proximity check.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { NgIf, UpperCasePipe, DecimalPipe } from '@angular/common';
import { SymbolUtils } from '../utils/symbol-utils';
import { Subscription } from 'rxjs';
import { IntelligenceApiService } from '../services/intelligence-api.service';
import { MarketIntelSnapshot } from '../models/intelligence.model';
import { ScalpingWsService, IntelligenceEvent } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';

@Component({
  selector: 'app-market-intel-panel',
  standalone: true,
  imports: [NgIf, UpperCasePipe, DecimalPipe],
  template: `
    <div class="intel-panel">
      <div class="panel-header">
        <span class="panel-title">Market Intelligence</span>
      </div>
      <div class="title-hr"></div>
      <div class="intel-grid">
        <div class="intel-item">
          <span class="label">Symbol</span>
          <span class="value" style="color: #F0B90B;">{{ symbol }}</span>
        </div>

        <!-- Signal Score with threshold proximity -->
        <div class="intel-item score-item">
          <span class="label">Signal Score</span>
          <div class="score-block">
            <span class="value score" [class.bullish]="signalBias === 'bullish'" [class.bearish]="signalBias === 'bearish'">
              {{ signalScore }}
            </span>
            <span class="threshold-label" *ngIf="signalThreshold !== null">
              / soglia {{ signalThreshold }}
            </span>
          </div>
        </div>

        <!-- Threshold proximity bar -->
        <div class="intel-item threshold-bar-item" *ngIf="signalThreshold !== null">
          <span class="label">Prossimità soglia</span>
          <div class="threshold-track-wrap">
            <div class="threshold-track">
              <div class="threshold-fill"
                [style.width.%]="getThresholdPct()"
                [class.close]="getThresholdPct() >= 80"
                [class.mid]="getThresholdPct() >= 50 && getThresholdPct() < 80"
                [class.far]="getThresholdPct() < 50">
              </div>
            </div>
            <span class="threshold-pct-label" [class.close]="getThresholdPct() >= 80">
              {{ getThresholdPct() | number:'1.0-0' }}%
            </span>
          </div>
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
          <span class="label">Fear &amp; Greed</span>
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
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .panel-header { margin-bottom: 10px; }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: 10px 0 12px 0; }
    .intel-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
    .intel-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: var(--bg-elevated); border-radius: 6px; }
    .label { font-size: 13px; color: var(--text-secondary); }
    .value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
    .value.score { font-size: 20px; font-weight: 700; }
    .value.bullish { color: var(--color-buy, #0ECB81); }
    .value.bearish { color: var(--color-sell, #F6465D); }
    .value.hot { color: var(--color-buy, #0ECB81); }
    .value.cold { color: var(--color-sell, #F6465D); }

    /* Score + threshold inline */
    .score-item { align-items: center; }
    .score-block { display: flex; align-items: baseline; gap: 6px; }
    .threshold-label {
      font-size: 11px;
      color: var(--text-secondary);
      opacity: 0.7;
      font-weight: 400;
      white-space: nowrap;
    }

    /* Threshold proximity bar */
    .threshold-bar-item { flex-direction: column; gap: 8px; align-items: stretch; }
    .threshold-track-wrap { display: flex; align-items: center; gap: 8px; width: 100%; }
    .threshold-track {
      flex: 1;
      height: 8px;
      background: rgba(255,255,255,0.08);
      border-radius: 4px;
      overflow: hidden;
    }
    .threshold-fill {
      height: 100%;
      border-radius: 4px;
      transition: width 0.5s ease, background-color 0.4s ease;
      min-width: 4px;
    }
    .threshold-fill.far  { background: linear-gradient(90deg, #555, #777); }
    .threshold-fill.mid  { background: linear-gradient(90deg, #ffb74d, #ffa726); }
    .threshold-fill.close { background: linear-gradient(90deg, #26a69a, #4db6ac); animation: pulse-bar 1.5s ease-in-out infinite; }
    @keyframes pulse-bar {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }
    .threshold-pct-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-secondary);
      width: 34px;
      text-align: right;
      flex-shrink: 0;
    }
    .threshold-pct-label.close { color: #26a69a; }
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
  signalThreshold: number | null = null;
  private _rawScore: number | null = null;

  /** Symbol shown in template — updated from active session */
  symbol: string = 'OKBEUR';
  private sub = new Subscription();

  constructor(
    private intelApi: IntelligenceApiService,
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Sync symbol and threshold from active session
    this.sub.add(
      this.sessionApi.session$.subscribe((session) => {
        if (session && session.symbol && session.status !== 'idle') {
          if (session.symbol !== this.symbol) {
            this.symbol = session.symbol;
            this.loadSnapshot();
          }
          // Read threshold from session response
          if ((session as unknown as Record<string, unknown>)['signal_strength_threshold'] !== undefined) {
            this.signalThreshold = (session as unknown as Record<string, unknown>)['signal_strength_threshold'] as number;
            this.cdr.detectChanges();
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
        if (data.symbol && !SymbolUtils.equals(data.symbol, this.symbol)) {
          return; // skip events for other symbols
        }
        if (data.signal_score !== undefined) {
          this._rawScore = data.signal_score;
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

  /**
   * Returns 0-100 representing how close the absolute score is to the threshold.
   * 100 = at or past threshold (trade imminent), 0 = score is 0.
   */
  getThresholdPct(): number {
    if (this._rawScore === null || this.signalThreshold === null || this.signalThreshold === 0) return 0;
    const pct = (Math.abs(this._rawScore) / Math.abs(this.signalThreshold)) * 100;
    return Math.min(100, Math.max(0, pct));
  }

  private loadSnapshot(): void {
    this.intelApi.getLatestSnapshot(this.symbol).subscribe({
      next: (data: MarketIntelSnapshot) => {
        if (data.signal_score !== undefined) {
          this._rawScore = data.signal_score;
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