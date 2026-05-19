import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { GenerationProgressStatus } from '../../../core/models/strategy.model';
import { NgClass } from '@angular/common';

interface Step {
  key: string;
  label: string;
}

@Component({
  selector: 'app-generation-progress',
  standalone: true,
  imports: [NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="progress-container" [ngClass]="status()">
      <div class="status-header">
        <div class="icon-wrapper">
          @if (status() === 'running' || status() === 'pending') {
            <div class="spinner"></div>
          } @else if (status() === 'completed') {
            <span class="icon" [class.success]="successCompletion()" [class.warn]="!successCompletion()">
              {{ successCompletion() ? '✓' : 'ⓘ' }}
            </span>
          } @else {
            <span class="icon error">!</span>
          }
        </div>
        <div class="text-group">
          <span class="status-title">{{ statusLabel() }}</span>
          <p class="status-subtitle">{{ statusDescription() }}</p>
        </div>
      </div>

      @if (status() !== 'completed' && status() !== 'failed') {
        <div class="stepper-wrapper">
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="progressPct()"></div>
          </div>
          <div class="stepper">
            @for (step of steps; track step.key; let i = $index) {
              <div class="step-item" [class.active]="stepState(i) === 'active'" [class.done]="stepState(i) === 'done'">
                <div class="step-marker">
                  <span class="step-icon">{{ stepIcon(i) }}</span>
                </div>
                <span class="step-label">{{ step.label }}</span>
              </div>
            }
          </div>
        </div>
      }

      @if (status() === 'completed') {
        <div class="stepper-wrapper">
          <div class="progress-bar">
            <div class="progress-fill done" [style.width.%]="100"></div>
          </div>
          <div class="stepper">
            @for (step of steps; track step.key) {
              <div class="step-item done">
                <div class="step-marker">
                  <span class="step-icon">✅</span>
                </div>
                <span class="step-label">{{ step.label }}</span>
              </div>
            }
          </div>
        </div>
      }

      @if (status() === 'failed') {
        <div class="stepper-wrapper">
          <div class="progress-bar">
            <div class="progress-fill failed" [style.width.%]="progressPct()"></div>
          </div>
          <div class="stepper">
            @for (step of steps; track step.key; let i = $index) {
              <div class="step-item" [class.active]="stepState(i) === 'active'" [class.done]="stepState(i) === 'done'">
                <div class="step-marker">
                  <span class="step-icon">{{ stepIcon(i) }}</span>
                </div>
                <span class="step-label">{{ step.label }}</span>
              </div>
            }
          </div>
        </div>
      }

      @if (detailMessage()) {
        <div class="detail-message" [class.detail-message--warn]="status() === 'completed' && !successCompletion()">
          {{ detailMessage() }}
        </div>
      }

      @if (status() === 'completed' && successCompletion()) {
        <div class="completion-banner">
          <span class="celebration">✨</span>
          <span>Abbiamo trovato le migliori opportunità per il tuo profilo!</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .progress-container {
      padding:32px;
      background:var(--bg-elevated,#161B22);
      border-radius:16px;
      border:1px solid var(--border-default);
      transition: all 0.3s ease;
    }
    .progress-container.completed { border-color: var(--color-buy); background: rgba(14, 203, 129, 0.05); }
    .progress-container.failed { border-color: var(--color-sell); background: rgba(246, 70, 93, 0.05); }

    .status-header { display:flex; align-items:center; gap:20px; margin-bottom:24px; }

    .icon-wrapper { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 12px; background: rgba(255,255,255,0.05); }

    .spinner { width: 24px; height: 24px; border: 3px solid rgba(240, 185, 11, 0.1); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .icon { font-size: 24px; font-weight: bold; }
    .icon.success { color: var(--color-buy); }
    .icon.warn { color: var(--accent-primary); }
    .icon.error { color: var(--color-sell); }

    .detail-message {
      margin-top: 16px; padding: 12px 14px; border-radius: 8px;
      font-size: 13px; line-height: 1.45; color: var(--text-secondary);
      background: rgba(255,255,255,0.04); border: 1px solid var(--border-default);
    }
    .detail-message--warn {
      border-color: rgba(240, 185, 11, 0.35);
      background: rgba(240, 185, 11, 0.06);
      color: var(--text-primary);
    }

    .text-group { display: flex; flex-direction: column; gap: 4px; }
    .status-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
    .status-subtitle { font-size: 14px; color: var(--text-secondary); margin: 0; }

    .stepper-wrapper { display: flex; flex-direction: column; gap: 16px; }
    .progress-bar { height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden; }
    .progress-fill { height:100%; background:var(--accent-primary); transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
    .progress-fill.failed { background: var(--color-sell); }
    .progress-fill.done { background: var(--color-buy); }

    .stepper { display: flex; justify-content: space-between; align-items: flex-start; }
    .step-item {
      display: flex; flex-direction: column; align-items: center; gap: 8px;
      flex: 1; position: relative;
    }
    .step-item:not(:last-child)::after {
      content: ''; position: absolute; top: 12px; left: 60%; right: -40%;
      height: 2px; background: rgba(255,255,255,0.08);
    }
    .step-item.done:not(:last-child)::after { background: var(--color-buy); }

    .step-marker {
      width: 26px; height: 26px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      background: rgba(255,255,255,0.05); border: 2px solid rgba(255,255,255,0.1);
      font-size: 13px; transition: all 0.3s;
    }
    .step-item.active .step-marker {
      border-color: var(--accent-primary);
      background: rgba(240, 185, 11, 0.15);
      box-shadow: 0 0 12px rgba(240, 185, 11, 0.25);
    }
    .step-item.done .step-marker {
      border-color: var(--color-buy);
      background: rgba(14, 203, 129, 0.15);
    }

    .step-icon { line-height: 1; }
    .step-label {
      font-size: 11px; color: var(--text-secondary); opacity: 0.5;
      text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;
      text-align: center; transition: all 0.3s;
    }
    .step-item.active .step-label { color: var(--accent-primary); opacity: 1; }
    .step-item.done .step-label { color: var(--color-buy); opacity: 1; }

    .completion-banner {
      display: flex; align-items: center; gap: 12px; padding: 12px 16px;
      background: rgba(14, 203, 129, 0.1); border-radius: 8px; color: var(--color-buy);
      font-size: 14px; font-weight: 500;
    }
    .celebration { font-size: 20px; }
  `]
})
export class GenerationProgressComponent {
  status = input.required<GenerationProgressStatus>();
  /** Messaggio da backend (vuoto / errore / filtri qualità). */
  detailMessage = input<string | null>(null);
  /** Numero strategie generate; se 0 con completed → UI neutra (HALU-FE-04). */
  resultCount = input<number | null>(null);

  steps: Step[] = [
    { key: 'analysis', label: 'Analisi Mercato' },
    { key: 'optimization', label: 'Ottimizzazione AI' },
    { key: 'backtest', label: 'Backtesting' },
  ];

  successCompletion = computed(() => {
    const st = this.status();
    if (st !== 'completed') return false;
    const n = this.resultCount();
    return n != null && n > 0;
  });

  progressPct = computed(() => {
    const st = this.status();
    if (st === 'pending') return 33;
    if (st === 'running') return 66;
    if (st === 'completed') return 100;
    return 33;
  });

  stepState(index: number): 'pending' | 'active' | 'done' {
    const st = this.status();
    if (st === 'pending') {
      if (index === 0) return 'active';
      return 'pending';
    }
    if (st === 'running') {
      if (index === 0) return 'done';
      if (index === 1) return 'active';
      return 'pending';
    }
    if (st === 'completed') {
      return 'done';
    }
    // failed
    if (index === 0) return 'done';
    if (index === 1) return 'active';
    return 'pending';
  }

  stepIcon(index: number): string {
    const state = this.stepState(index);
    if (state === 'done') return '✅';
    if (state === 'active') return '⏳';
    return '○';
  }

  statusLabel(): string {
    const st = this.status();
    if (st === 'completed' && !this.successCompletion()) {
      return 'Generazione terminata';
    }
    const labels: Record<string, string> = {
      pending: 'Inizializzazione AI',
      running: 'Elaborazione in corso',
      completed: 'Generazione Completata',
      failed: 'Errore di Generazione'
    };
    return labels[st] || st;
  }

  statusDescription(): string {
    const st = this.status();
    if (st === 'completed' && !this.successCompletion()) {
      return 'Nessuna strategia supera i criteri oppure i dati di mercato non sono disponibili. Leggi il messaggio qui sotto.';
    }
    const desc: Record<string, string> = {
      pending: 'Stiamo preparando i modelli per la tua richiesta...',
      running: 'Analizzando pattern storici e ottimizzando i parametri...',
      completed: 'Le strategie sono pronte per essere revisionate.',
      failed: 'Non è stato possibile completare la richiesta. Riprova tra poco.'
    };
    return desc[st] || '';
  }
}