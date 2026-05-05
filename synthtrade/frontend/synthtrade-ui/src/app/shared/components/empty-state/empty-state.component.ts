import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="empty-state">
      <span class="icon">{{ icon() }}</span>
      <p class="message">{{ message() }}</p>
    </div>
  `,
  styles: [`
    .empty-state { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:48px; gap:12px; }
    .icon { font-size:32px; }
    .message { color:var(--text-muted,#474D57); font-size:14px; }
  `]
})
export class EmptyStateComponent {
  message = input<string>('Nessun dato disponibile');
  icon = input<string>('📭');
}
