/**
 * Signal Scorecard Component
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { ScalpingWsService, IntelligenceEvent } from '../services/scalping-ws.service';

@Component({
  selector: 'app-signal-scorecard',
  standalone: true,
  template: `
    <div class="scorecard">
      <span class="panel-title">Signal Score</span>
      <div class="score-display">
        <div class="score-circle"><span class="score-value">{{ score }}</span></div>
        <div class="bias" [class.bullish]="bias === 'bullish'" [class.bearish]="bias === 'bearish'">{{ bias }}</div>
      </div>
    </div>
  `,
  styles: [`
    .scorecard { padding: 12px; }
    .panel-title { font-size: 13px; font-weight: 500; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    .score-display { display: flex; align-items: center; gap: 12px; }
    .score-circle { width: 60px; height: 60px; border-radius: 50%; background: var(--bg-elevated); display: flex; align-items: center; justify-content: center; }
    .score-value { font-size: 18px; font-weight: 700; }
    .bias { font-size: 12px; padding: 4px 8px; border-radius: 4px; background: var(--bg-elevated); }
    .bias.bullish { color: #26a69a; }
    .bias.bearish { color: #ef5350; }
  `],
})
export class SignalScorecardComponent implements OnInit, OnDestroy {
  score = 50;
  bias: 'bullish' | 'bearish' | 'neutral' = 'neutral';
  private sub?: Subscription;

  constructor(private ws: ScalpingWsService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.sub = this.ws.intelligence$.pipe(
      filter(data => data !== null)
    ).subscribe((data: IntelligenceEvent) => {
      if (data.signal_score !== undefined) {
        this.score = Math.round(data.signal_score);
      }
      if (data.signal_bias) {
        this.bias = data.signal_bias;
      }
      this.cdr.detectChanges();
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}