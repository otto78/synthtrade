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
     .modal { background:var(--bg-elevated,#161B22); border-radius:16px; padding:28px; min-width:280px; max-width:360px; width:90%; box-shadow:0 8px 24px rgba(0,0,0,0.4); }
     .modal-actions { display:flex; gap:12px; justify-content:flex-end; margin-top:20px; }
     .btn-danger { background:var(--color-sell,#F6465D); color:#fff; border:none; padding:10px 20px; font-size:15px; font-weight:600; border-radius:6px; cursor:pointer; transition:all 0.2s; }
     .btn-danger:hover { opacity:0.9; transform:translateY(-2px); }
     .btn-ghost  { background:transparent; color:var(--text-primary,#FFFFFF); border:1px solid var(--border-default); padding:10px 20px; font-size:15px; font-weight:600; border-radius:6px; cursor:pointer; transition:all 0.2s; }
     .btn-ghost:hover { opacity:0.9; transform:translateY(-2px); }
     p { font-size:16px; line-height:1.5; color:var(--text-primary,#FFFFFF); margin:0 0 16px 0; }
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
