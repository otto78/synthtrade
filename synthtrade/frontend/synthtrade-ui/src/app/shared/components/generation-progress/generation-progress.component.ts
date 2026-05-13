import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { GenerationProgressStatus } from '../../../core/models/strategy.model';
import { NgClass } from '@angular/common';

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
      
      @if (status() === 'running' || status() === 'pending') {
        <div class="progress-wrapper">
          <div class="progress-bar">
            <div class="progress-fill animate"></div>
          </div>
          <div class="steps">
            <span class="step active">Analisi Mercato</span>
            <span class="step" [class.active]="status() === 'running'">Ottimizzazione AI</span>
            <span class="step">Backtesting</span>
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
    
    .progress-wrapper { display: flex; flex-direction: column; gap: 12px; }
    .progress-bar { height:6px; background:rgba(255,255,255,0.05); border-radius:3px; overflow:hidden; }
    .progress-fill { height:100%; background:var(--accent-primary); width:0; }
    .progress-fill.animate { width: 100%; transition: width 30s cubic-bezier(0.1, 0, 0.4, 1); }
    
    .steps { display: flex; justify-content: space-between; }
    .step { font-size: 11px; color: var(--text-secondary); opacity: 0.5; text-transform: uppercase; letter-spacing: 0.5px; }
    .step.active { color: var(--accent-primary); opacity: 1; font-weight: 600; }

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

  successCompletion = computed(() => {
    const st = this.status();
    if (st !== 'completed') return false;
    const n = this.resultCount();
    return n != null && n > 0;
  });

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
