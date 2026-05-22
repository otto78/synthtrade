import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  imports: [NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loading()) {
      <div class="stat-card skeleton"></div>
    } @else {
      <div class="stat-card">
        <span class="label">{{ label() }}</span>
        <span class="value" [ngClass]="{ positive: (delta() ?? 0) > 0, negative: (delta() ?? 0) < 0 }">
          {{ value() }}
        </span>
        @if (delta() !== null && delta() !== undefined) {
          <span class="delta">{{ (delta()! > 0 ? '+' : '') + delta()!.toFixed(2) }}%</span>
        }
      </div>
    }
  `,
  styles: [`
    .stat-card { padding: 16px; background: var(--bg-surface); border-radius: 8px; min-height: 120px; display: flex; flex-direction: column; justify-content: center; }
    .label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
    .value { display: block; font-size: 24px; font-family: var(--font-mono, monospace); color: var(--text-primary); }
    .value.positive { color: var(--color-buy); }
    .value.negative { color: var(--color-sell); }
    .delta { font-size: 12px; color: var(--text-secondary); }
    .skeleton { height: 100px; background: var(--bg-elevated); animation: pulse 1.5s ease-in-out infinite; border-radius: 8px; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  `]
})
export class StatCardComponent {
  label = input.required<string>();
  value = input.required<string>();
  delta = input<number | null>(null);
  loading = input<boolean>(false);
}
