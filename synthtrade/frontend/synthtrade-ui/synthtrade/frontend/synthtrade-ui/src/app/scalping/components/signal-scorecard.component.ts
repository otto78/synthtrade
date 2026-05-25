/**
 * Signal Scorecard Component
 * Displays aggregate score 0-100 with breakdown
 */

import { Component } from '@angular/core';

@Component({
  selector: 'app-signal-scorecard',
  standalone: true,
  template: `
    <div class="scorecard">
      <h3>Signal Score</h3>

      <div class="score-display">
        <div class="score-circle" [style.--score]="score">
          <span class="score-value">{{ score }}</span>
        </div>
        <div class="bias" [class.bullish]="bias === 'bullish'" [class.bearish]="bias === 'bearish'">
          {{ bias }}
        </div>
      </div>

      <div class="breakdown">
        <div class="breakdown-item" *ngFor="let item of breakdown | keyvalue">
          <span class="name">{{ item.key }}</span>
          <span class="value">{{ item.value }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .scorecard {
      padding: 12px;
    }
    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--text-secondary);
    }
    .score-display {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }
    .score-circle {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: conic-gradient(
        var(--accent-primary, #F0B90B) 0% var(--score, 50) * 1%,
        var(--bg-elevated, #0D1117) var(--score, 50) * 1% 100%
      );
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .score-value {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .bias {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 4px;
      background: var(--bg-elevated);
    }
    .bias.bullish { color: #26a69a; }
    .bias.bearish { color: #ef5350; }
    .breakdown {
      font-size: 11px;
    }
    .breakdown-item {
      display: flex;
      justify-content: space-between;
      padding: 4px 0;
    }
  `],
})
export class SignalScorecardComponent {
  score = 50;
  bias: 'bullish' | 'bearish' | 'neutral' = 'neutral';
  breakdown: Record<string, number> = {
    funding: 25,
    cvd: 20,
    oi: 15,
  };
}