import { ChangeDetectionStrategy, Component, HostListener, input, output } from '@angular/core';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (visible()) {
      <div class="modal-overlay" (click)="cancelled.emit()">
        <div class="modal" (click)="$event.stopPropagation()">
          <p>{{ message() }}</p>
          <div class="modal-actions">
            <button class="btn-danger" (click)="confirmed.emit()">Conferma</button>
            <button class="btn-ghost" (click)="cancelled.emit()">Annulla</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:1000; }
    .modal { background:var(--bg-elevated,#161B22); border-radius:12px; padding:24px; min-width:320px; }
    .modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:16px; }
    .btn-danger { background:var(--color-sell,#F6465D); color:#fff; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; }
    .btn-ghost  { background:transparent; color:var(--text-secondary,#848E9C); border:1px solid var(--border-default); padding:8px 16px; border-radius:4px; cursor:pointer; }
  `]
})
export class ConfirmDialogComponent {
  visible = input.required<boolean>();
  message = input<string>('Sei sicuro?');
  confirmed = output<void>();
  cancelled = output<void>();

  @HostListener('document:keydown', ['$event'])
  onKeydown(e: KeyboardEvent): void {
    if (e.key === 'Escape' && this.visible()) this.cancelled.emit();
  }
}
