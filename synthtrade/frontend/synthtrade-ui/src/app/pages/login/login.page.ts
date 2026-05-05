import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="login-wrapper">
      <div class="login-card">
        <h1 class="logo">SynthTrade</h1>
        <p class="tagline">Synthetic intelligence. Real profits.</p>

        <form [formGroup]="form" (ngSubmit)="submit()">
          <div class="field">
            <input
              type="password"
              formControlName="password"
              placeholder="Password"
              autocomplete="current-password"
            />
          </div>

          @if (error()) {
            <p class="error">{{ error() }}</p>
          }

          <button type="submit" [disabled]="form.invalid || loading()">
            @if (loading()) {
              <span class="spinner"></span>
            } @else {
              Accedi
            }
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-wrapper {
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      background: var(--bg-base, #07090C);
    }
    .login-card {
      width: 360px; padding: 40px; background: var(--bg-surface, #0D1117);
      border-radius: 12px; border: 1px solid var(--border-default, rgba(234,236,239,0.06));
    }
    .logo { font-family: 'Chakra Petch', sans-serif; color: var(--accent-primary, #F0B90B); font-size: 24px; margin: 0 0 4px; }
    .tagline { color: var(--text-muted, #474D57); font-size: 12px; margin: 0 0 32px; }
    .field { margin-bottom: 16px; }
    input {
      width: 100%; padding: 10px 14px; background: var(--bg-elevated, #161B22);
      border: 1px solid var(--border-default, rgba(234,236,239,0.06)); border-radius: 4px;
      color: var(--text-primary, #EAECEF); font-size: 14px; box-sizing: border-box;
    }
    input:focus { outline: none; border-color: var(--border-focus, rgba(240,185,11,0.4)); }
    .error { color: var(--color-sell, #F6465D); font-size: 13px; margin: 0 0 12px; }
    button {
      width: 100%; padding: 10px; background: var(--accent-primary, #F0B90B);
      color: #000; border: none; border-radius: 4px; font-weight: 600;
      cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center;
    }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .spinner {
      width: 16px; height: 16px; border: 2px solid rgba(0,0,0,0.3);
      border-top-color: #000; border-radius: 50%; animation: spin 0.6s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class LoginPage {
  private auth = inject(AuthService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  form = this.fb.group({ password: ['', Validators.required] });
  loading = signal(false);
  error = signal('');

  submit(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set('');
    this.auth.login(this.form.value.password!).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.status === 401 ? 'Password errata' : 'Errore di connessione');
      },
    });
  }
}
