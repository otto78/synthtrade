import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [AsyncPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <div class="topbar-left">
        <span class="status-dot"></span>
        <span class="status-label">LIVE</span>
      </div>
      <div class="topbar-right">
        <span class="username">{{ auth.currentUser$ | async }}</span>
        <button class="btn-logout" (click)="auth.logout()">Logout</button>
      </div>
    </header>
  `,
  styles: [`
    .topbar {
      height: 56px; background: var(--bg-surface, #0D1117); display: flex;
      align-items: center; justify-content: space-between; padding: 0 24px;
      border-bottom: 1px solid var(--border-default, rgba(234,236,239,0.06));
      flex-shrink: 0;
    }
    .topbar-left, .topbar-right { display: flex; align-items: center; gap: 12px; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-buy, #0ECB81); }
    .status-label { font-size: 11px; font-family: monospace; color: var(--color-buy, #0ECB81); letter-spacing: 1px; }
    .username { font-size: 13px; color: var(--text-secondary, #848E9C); }
    .btn-logout {
      background: none; border: 1px solid var(--border-default, rgba(234,236,239,0.06));
      color: var(--text-secondary, #848E9C); padding: 4px 12px; border-radius: 4px;
      cursor: pointer; font-size: 12px; transition: color 0.2s;
    }
    .btn-logout:hover { color: var(--color-sell, #F6465D); border-color: var(--color-sell, #F6465D); }
  `]
})
export class TopbarComponent {
  auth = inject(AuthService);
}
