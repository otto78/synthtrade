import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { GenerationProgressStatus } from '../../../core/models/strategy.model';

@Component({
  selector: 'app-generation-progress',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="progress-container">
      <div class="status-header">
        <span class="status-dot" [class]="status()"></span>
        <span class="status-text">{{ statusLabel() }}</span>
      </div>
      
      @if (status() === 'running' || status() === 'pending') {
        <div class="progress-bar">
          <div class="progress-fill animate"></div>
        </div>
        <p class="hint">L'AI sta analizzando la tua richiesta...</p>
      }

      @if (status() === 'completed') {
        <p class="success">Generazione completata! Analizza i risultati qui sotto.</p>
      }

      @if (status() === 'failed') {
        <p class="error">Si è verificato un errore durante la generazione. Riprova.</p>
      }
    </div>
  `,
  styles: [`
    .progress-container { padding:20px; background:var(--bg-elevated,#161B22); border-radius:8px; border:1px solid var(--border-default); }
    .status-header { display:flex; align-items:center; gap:8px; margin-bottom:12px; }
    .status-dot { width:8px; height:8px; border-radius:50%; }
    .status-dot.pending { background: #848E9C; }
    .status-dot.running { background: #F0B90B; box-shadow: 0 0 8px #F0B90B; }
    .status-dot.completed { background: #0ECB81; }
    .status-dot.failed { background: #F6465D; }
    .status-text { font-weight:600; text-transform:capitalize; }
    
    .progress-bar { height:4px; background:var(--border-default); border-radius:2px; overflow:hidden; margin:8px 0; }
    .progress-fill { height:100%; background:var(--color-primary,#F0B90B); width:0; }
    .progress-fill.animate { width: 100%; transition: width 30s linear; }
    
    .hint { font-size:12px; color:var(--text-secondary); }
    .success { color:var(--color-buy); }
    .error { color:var(--color-sell); }
  `]
})
export class GenerationProgressComponent {
  status = input.required<GenerationProgressStatus>();

  statusLabel(): string {
    const labels: Record<string, string> = {
      pending: 'In attesa...',
      running: 'Generazione in corso...',
      completed: 'Completato',
      failed: 'Errore'
    };
    return labels[this.status()] || this.status();
  }
}
