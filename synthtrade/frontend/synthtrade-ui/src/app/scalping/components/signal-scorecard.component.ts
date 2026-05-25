/**
 * Signal Scorecard Component
 */

import { Component } from '@angular/core';

@Component({
  selector: 'app-signal-scorecard',
  standalone: true,
  template: `
    <div class="scorecard">
      <h3>Signal Score</h3>
      <div class="score-display">
        <div class="score-circle"><span class="score-value">{{ score }}</span></div>
        <div class="bias" [class.bullish]="bias === 'bullish'" [class.bearish]="bias === 'bearish'">{{ bias }}</div>
      </div>
    </div>
  `,
  styles: [`
    .scorecard { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .score-display { display: flex; align-items: center; gap: 12px; }
    .score-circle { width: 60px; height: 60px; border-radius: 50%; background: var(--bg-elevated); display: flex; align-items: center; justify-content: center; }
    .score-value { font-size: 18px; font-weight: 700; }
    .bias { font-size: 12px; padding: 4px 8px; border-radius: 4px; background: var(--bg-elevated); }
    .bias.bullish { color: #26a69a; }
    .bias.bearish { color: #ef5350; }
  `],
})
export class SignalScorecardComponent {
  score = 50;
  bias: 'bullish' | 'bearish' | 'neutral' = 'neutral';
}