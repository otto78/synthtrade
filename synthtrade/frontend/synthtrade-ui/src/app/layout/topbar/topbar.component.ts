import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { ConfigService } from '../../core/services/config.service';
import { BehaviorSubject, tap, catchError, of } from 'rxjs';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [AsyncPipe, ConfirmDialogComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <div class="topbar-left">
        <!-- Badge modalità cliccabile — molto più visibile -->
        <button
          class="mode-badge"
          [class.test]="(mode$ | async)?.mode === 'test'"
          [class.live]="(mode$ | async)?.mode === 'live'"
          (click)="toggleDropdown()"
          title="Cambia modalità trading"
        >
          <span class="mode-badge-indicator"></span>
          <span class="mode-badge-label">
            {{ (mode$ | async)?.mode === 'live' ? 'LIVE' : 'TEST' }}
          </span>
          <span class="mode-badge-arrow">▾</span>
        </button>

        <span class="status-detail">{{ (mode$ | async)?.details }}</span>

        <!-- Dropdown modalità -->
        @if (dropdownOpen) {
          <div class="mode-dropdown">
            <div class="dropdown-header">
              <div class="dropdown-title">Modalità trading</div>
              <div
                class="dropdown-current"
                [class.test]="(mode$ | async)?.mode === 'test'"
                [class.live]="(mode$ | async)?.mode === 'live'"
              >
                <span class="dropdown-indicator"></span>
                {{ (mode$ | async)?.mode === 'live' ? 'LIVE' : 'TEST' }}
              </div>
              <p class="dropdown-detail">{{ (mode$ | async)?.details }}</p>
            </div>

            <div class="dropdown-actions">
              @if ((mode$ | async)?.mode === 'test') {
                @if ((mode$ | async)?.allow_live) {
                  <button
                    class="btn-switch btn-live"
                    [disabled]="switchDisabled$ | async"
                    (click)="openLiveConfirm()"
                  >
                    ⚡ Passa a LIVE
                  </button>
                } @else {
                  <div class="blocked-banner">
                    <div class="blocked-title">🔒 LIVE bloccato</div>
                    <div class="blocked-hint">
                      Imposta <code>ALLOW_LIVE_MODE=true</code> nel file
                      <code>.env</code> del backend e riavvia.
                    </div>
                  </div>
                }
              }
              @if ((mode$ | async)?.mode === 'live') {
                <button
                  class="btn-switch btn-test"
                  [disabled]="switchDisabled$ | async"
                  (click)="switchMode('test')"
                >
                  🔄 Torna a TEST
                </button>
              }
            </div>
          </div>
        }
      </div>

      <div class="topbar-right">
        <span class="username">{{ auth.currentUser$ | async }}</span>
        <button class="btn-logout" (click)="auth.logout()">Logout</button>
      </div>
    </header>

    <!-- Toast per notifiche -->
    @if (toastMessage) {
      <div class="toast" [class.toast-error]="toastType === 'error'" [class.toast-success]="toastType === 'success'">
        {{ toastMessage }}
      </div>
    }

    <!-- Modal di conferma per passaggio a LIVE -->
    <app-confirm-dialog
      [visible]="confirmVisible"
      [message]="confirmMessage"
      (confirmed)="onLiveConfirmed()"
      (cancelled)="onLiveCancelled()"
    />
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

    /* Badge modalità — ben visibile, sembra un pulsante */
    .mode-badge {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px 6px 10px;
      border-radius: 20px;
      border: 1px solid rgba(234,236,239,0.1);
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
      font-family: monospace;
      letter-spacing: 1px;
      text-transform: uppercase;
      transition: all 0.2s ease;
      background: transparent;
    }
    .mode-badge:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .mode-badge.test {
      color: #F0B90B;
      border-color: rgba(240,185,11,0.3);
      background: rgba(240,185,11,0.08);
    }
    .mode-badge.test:hover {
      background: rgba(240,185,11,0.15);
      border-color: rgba(240,185,11,0.5);
    }
    .mode-badge.live {
      color: #0ECB81;
      border-color: rgba(14,203,129,0.3);
      background: rgba(14,203,129,0.08);
    }
    .mode-badge.live:hover {
      background: rgba(14,203,129,0.15);
      border-color: rgba(14,203,129,0.5);
    }
    .mode-badge-indicator {
      width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    }
    .mode-badge.test .mode-badge-indicator { background: #F0B90B; }
    .mode-badge.live .mode-badge-indicator { background: #0ECB81; }
    .mode-badge-label { line-height: 1; }
    .mode-badge-arrow {
      font-size: 8px; opacity: 0.6; margin-left: 2px;
    }

    .status-detail {
      font-size: 11px; color: var(--text-secondary, #848E9C);
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
      border-radius: 12px; padding: 16px; min-width: 300px;
      box-shadow: 0 12px 32px rgba(0,0,0,0.4);
      z-index: 200;
    }
    .dropdown-header { margin-bottom: 12px; }
    .dropdown-title {
      font-size: 11px; color: var(--text-secondary, #848E9C);
      text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    }
    .dropdown-current {
      display: flex; align-items: center; gap: 8px;
      font-size: 16px; font-weight: 700; font-family: monospace;
    }
    .dropdown-current.test { color: #F0B90B; }
    .dropdown-current.live { color: #0ECB81; }
    .dropdown-indicator {
      width: 10px; height: 10px; border-radius: 50%; display: inline-block;
    }
    .dropdown-current.test .dropdown-indicator { background: #F0B90B; }
    .dropdown-current.live .dropdown-indicator { background: #0ECB81; }
    .dropdown-detail { font-size: 11px; color: var(--text-secondary, #848E9C); margin-top: 4px; }
    .dropdown-actions { display: flex; flex-direction: column; gap: 8px; }

    .btn-switch {
      border: none; padding: 10px 16px; border-radius: 8px;
      cursor: pointer; font-size: 13px; font-weight: 600;
      transition: all 0.2s;
      width: 100%;
      text-align: center;
    }
    .btn-switch:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .btn-switch:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
    .btn-live {
      background: linear-gradient(135deg, #0ECB81, #06a86a);
      color: #000;
    }
    .btn-test {
      background: #F0B90B; color: #000;
    }

    .blocked-banner {
      background: rgba(246,70,93,0.08);
      border: 1px solid rgba(246,70,93,0.2);
      border-radius: 8px; padding: 12px;
    }
    .blocked-title {
      font-size: 13px; font-weight: 600; color: var(--color-sell, #F6465D); margin-bottom: 6px;
    }
    .blocked-hint {
      font-size: 11px; color: var(--text-secondary, #848E9C); line-height: 1.4;
    }
    .blocked-hint code {
      font-family: monospace; background: rgba(255,255,255,0.06);
      padding: 1px 4px; border-radius: 2px;
    }

    /* Toast notification */
    .toast {
      position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
      padding: 12px 24px; border-radius: 8px;
      font-size: 13px; font-weight: 500;
      z-index: 9999;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      animation: fadeInUp 0.3s ease;
    }
    .toast-error { background: var(--color-sell, #F6465D); color: #fff; }
    .toast-success { background: var(--color-buy, #0ECB81); color: #000; }
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateX(-50%) translateY(20px); }
      to { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
  `]
})
export class TopbarComponent {
  auth = inject(AuthService);
  configService = inject(ConfigService);

  mode$ = this.configService.getMode();
  dropdownOpen = false;
  switchDisabled$ = new BehaviorSubject(false);
  toastMessage = '';
  toastType: 'success' | 'error' = 'success';
  private toastTimer: ReturnType<typeof setTimeout> | null = null;

  // Confirm dialog per switch a LIVE
  confirmVisible = false;
  confirmMessage = '';

  toggleDropdown(): void {
    this.dropdownOpen = !this.dropdownOpen;
  }

  openLiveConfirm(): void {
    this.confirmMessage =
      '⚠️ ATTENZIONE: Stai per passare a modalità LIVE!\n\n' +
      'Tutti i dati (strategie, trade, log) mostreranno solo dati LIVE.\n' +
      'I fondi reali potrebbero essere coinvolti.\n\n' +
      'Sei sicuro?';
    this.confirmVisible = true;
  }

  onLiveConfirmed(): void {
    this.confirmVisible = false;
    this.switchMode('live');
  }

  onLiveCancelled(): void {
    this.confirmVisible = false;
  }

  switchMode(mode: 'test' | 'live'): void {
    this.switchDisabled$.next(true);
    this.configService.setMode(mode).pipe(
      tap(() => {
        this.configService.invalidateCache();
        this.mode$ = this.configService.getMode();
        this.dropdownOpen = false;
        this.showToast(
          mode === 'live' ? '✅ Passato a modalità LIVE' : '🔄 Passato a modalità TEST',
          'success'
        );
        // Ricarica la pagina dopo 800ms per dare tempo al toast di mostrarsi
        // e garantire che tutti i componenti si reinizializzino con la nuova modalità
        setTimeout(() => window.location.reload(), 800);
      }),
      catchError((err) => {
        const msg = err?.error?.detail || err?.message || 'Errore sconosciuto';
        this.showToast(`❌ ${msg}`, 'error');
        return of(null);
      }),
      tap(() => this.switchDisabled$.next(false))
    ).subscribe();
  }

  private showToast(message: string, type: 'success' | 'error'): void {
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastMessage = message;
    this.toastType = type;
    this.toastTimer = setTimeout(() => {
      this.toastMessage = '';
      this.toastTimer = null;
    }, 4000);
  }
}