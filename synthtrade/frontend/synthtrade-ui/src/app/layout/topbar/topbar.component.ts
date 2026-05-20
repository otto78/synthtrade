import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe, NgIf } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { ConfigService } from '../../core/services/config.service';
import { BehaviorSubject, tap, catchError, of } from 'rxjs';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [AsyncPipe, NgIf],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <div class="topbar-left">
        <span
          class="status-dot"
          [class.test]="(mode$ | async)?.mode === 'test'"
          [class.live]="(mode$ | async)?.mode === 'live'"
          (click)="toggleDropdown()"
        ></span>
        <span
          class="status-label"
          [class.test]="(mode$ | async)?.mode === 'test'"
          [class.live]="(mode$ | async)?.mode === 'live'"
        >
          {{ (mode$ | async)?.mode === 'live' ? 'LIVE' : 'TEST' }}
        </span>
        <span class="status-detail">{{ (mode$ | async)?.details }}</span>

        <!-- TASK-431: Dropdown modalità -->
        <div *ngIf="dropdownOpen" class="mode-dropdown">
          <div class="dropdown-header">
            <span class="dropdown-label">Modalità attuale:</span>
            <span class="dropdown-value" [class.test]="(mode$ | async)?.mode === 'test'" [class.live]="(mode$ | async)?.mode === 'live'">
              {{ (mode$ | async)?.mode === 'live' ? '🔴 LIVE' : '🟡 TEST' }}
            </span>
            <p class="dropdown-detail">{{ (mode$ | async)?.details }}</p>
          </div>
          <div class="dropdown-actions">
            <button
              *ngIf="(mode$ | async)?.mode === 'test'"
              class="btn-switch"
              [disabled]="switchDisabled$ | async"
              (click)="switchMode('live')"
            >
              {{ (mode$ | async)?.allow_live ? 'Switch to LIVE' : 'LIVE bloccato (ALLOW_LIVE_MODE=false)' }}
            </button>
            <button
              *ngIf="(mode$ | async)?.mode === 'live'"
              class="btn-switch btn-test"
              (click)="switchMode('test')"
            >
              Switch to TEST
            </button>
          </div>
          <div *ngIf="(mode$ | async)?.mode === 'test' && !(mode$ | async)?.allow_live" class="dropdown-hint">
            ⚠️ Per abilitare LIVE, imposta <code>ALLOW_LIVE_MODE=true</code> nel file .env del backend
          </div>
        </div>
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
      position: relative;
      z-index: 100;
    }
    .topbar-left, .topbar-right { display: flex; align-items: center; gap: 12px; }
    .status-dot {
      width: 10px; height: 10px; border-radius: 50%;
      cursor: pointer; transition: transform 0.2s;
    }
    .status-dot:hover { transform: scale(1.3); }
    .status-dot.live { background: var(--color-buy, #0ECB81); }
    .status-dot.test { background: #F0B90B; } /* giallo Binance testnet */
    .status-label {
      font-size: 11px; font-family: monospace; letter-spacing: 1px;
      cursor: pointer;
    }
    .status-label.live { color: var(--color-buy, #0ECB81); }
    .status-label.test { color: #F0B90B; }
    .status-detail {
      font-size: 11px; color: var(--text-secondary, #848E9C);
      margin-left: 8px;
    }
    .username { font-size: 13px; color: var(--text-secondary, #848E9C); }
    .btn-logout {
      background: none; border: 1px solid var(--border-default, rgba(234,236,239,0.06));
      color: var(--text-secondary, #848E9C); padding: 4px 12px; border-radius: 4px;
      cursor: pointer; font-size: 12px; transition: color 0.2s;
    }
    .btn-logout:hover { color: var(--color-sell, #F6465D); border-color: var(--color-sell, #F6465D); }

    /* Dropdown */
    .mode-dropdown {
      position: absolute; top: 50px; left: 24px;
      background: var(--bg-surface, #0D1117);
      border: 1px solid var(--border-default, rgba(234,236,239,0.12));
      border-radius: 8px; padding: 16px; min-width: 280px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      z-index: 200;
    }
    .dropdown-header { margin-bottom: 12px; }
    .dropdown-label { font-size: 11px; color: var(--text-secondary, #848E9C); }
    .dropdown-value { font-size: 14px; font-weight: 600; font-family: monospace; margin-left: 4px; }
    .dropdown-value.live { color: var(--color-buy, #0ECB81); }
    .dropdown-value.test { color: #F0B90B; }
    .dropdown-detail { font-size: 11px; color: var(--text-secondary, #848E9C); margin-top: 4px; }
    .dropdown-actions { display: flex; flex-direction: column; gap: 8px; }
    .btn-switch {
      background: var(--color-buy, #0ECB81); color: #000;
      border: none; padding: 8px 16px; border-radius: 6px;
      cursor: pointer; font-size: 12px; font-weight: 600;
      transition: opacity 0.2s;
    }
    .btn-switch:hover:not(:disabled) { opacity: 0.8; }
    .btn-switch:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-switch.btn-test { background: #F0B90B; color: #000; }
    .dropdown-hint {
      font-size: 11px; color: var(--color-sell, #F6465D);
      margin-top: 8px; padding: 8px; background: rgba(246,70,93,0.08);
      border-radius: 4px;
    }
    .dropdown-hint code {
      font-family: monospace; background: rgba(255,255,255,0.06);
      padding: 1px 4px; border-radius: 2px;
    }
  `]
})
export class TopbarComponent {
  auth = inject(AuthService);
  configService = inject(ConfigService);

  mode$ = this.configService.getMode();
  dropdownOpen = false;
  switchDisabled$ = new BehaviorSubject(false);

  toggleDropdown(): void {
    this.dropdownOpen = !this.dropdownOpen;
  }

  switchMode(mode: 'test' | 'live'): void {
    if (mode === 'live') {
      const confirmed = confirm(
        '⚠️ ATTENZIONE: Stai per passare a modalità LIVE!\n\n' +
        'Tutti i dati (strategie, trade, log) mostreranno solo dati LIVE.\n' +
        'I fondi reali potrebbero essere coinvolti.\n\n' +
        'Sei sicuro?'
      );
      if (!confirmed) return;
    }

    this.switchDisabled$.next(true);
    this.configService.setMode(mode).pipe(
      tap(() => {
        this.configService.invalidateCache();
        this.mode$ = this.configService.getMode();
        this.dropdownOpen = false;
      }),
      catchError((err) => {
        alert(`Errore nel cambio modalità: ${err.message || err}`);
        return of(null);
      }),
      tap(() => this.switchDisabled$.next(false))
    ).subscribe();
  }
}