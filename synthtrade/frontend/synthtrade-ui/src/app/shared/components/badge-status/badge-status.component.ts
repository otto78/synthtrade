import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'app-badge-status',
  standalone: true,
  imports: [NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="badge" [ngClass]="statusClass()">{{ status() }}</span>`,
  styles: [`
    .badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-family: monospace; }
    .badge--active   { color: var(--color-buy);  background: rgba(14,203,129,0.1); }
    .badge--pending  { color: var(--color-warn); background: rgba(240,185,11,0.1); }
    .badge--rejected { color: var(--color-sell); background: rgba(246,70,93,0.1); }
  `]
})
export class BadgeStatusComponent {
  status = input.required<string>();

  statusClass = computed(() => ({
    'badge--active':   ['ACTIVE', 'APPROVED'].includes(this.status()),
    'badge--pending':  this.status() === 'PENDING',
    'badge--rejected': ['REJECTED', 'EXPIRED'].includes(this.status()),
  }));
}
