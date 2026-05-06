import { ChangeDetectionStrategy, Component, output, signal, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { StrategyRequest, RiskLevel, AssetClass } from '../../../core/models/strategy.model';
import { NgClass, TitleCasePipe } from '@angular/common';

@Component({
  selector: 'app-strategy-request-form',
  standalone: true,
  imports: [ReactiveFormsModule, NgClass, TitleCasePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" class="request-form">
      <div class="form-row">
        <div class="form-group flex-1">
          <label>Budget (EUR)</label>
          <div class="input-wrapper">
            <span class="prefix">€</span>
            <input type="number" formControlName="budget_eur" placeholder="Es. 100">
          </div>
        </div>

        <div class="form-group flex-1">
          <label>Durata (Giorni)</label>
          <input type="number" formControlName="duration_days" placeholder="Es. 30">
        </div>
      </div>

      <div class="form-row">
        <div class="form-group flex-1">
          <label>Classe Asset</label>
          <select formControlName="asset_class">
            <option value="crypto">Criptovalute</option>
            <option value="stocks">Azioni (Coming Soon)</option>
            <option value="forex">Forex (Coming Soon)</option>
          </select>
        </div>

        <div class="form-group flex-1">
          <label>Livello di Rischio</label>
          <div class="risk-selector">
            @for (level of riskLevels; track level) {
              <button 
                type="button" 
                [class]="'risk-btn risk-btn--' + level"
                [class.active]="isRiskActive(level)"
                (click)="setRiskLevel(level)"
              >
                {{ level | titlecase }}
              </button>
            }
          </div>
        </div>
      </div>

      <div class="form-group">
        <label>Simboli Specifici (opzionale)</label>
        <div class="symbol-input-container">
          <div class="chips">
            @for (symbol of selectedSymbols(); track symbol) {
              <span class="chip">
                {{ symbol }}
                <button type="button" class="remove-chip" (click)="removeSymbol(symbol)">×</button>
              </span>
            }
          </div>
          <input 
            #symbolInput
            type="text" 
            placeholder="Aggiungi simbolo (es. BTCUSDT)" 
            (keydown.enter)="$event.preventDefault(); addSymbol(symbolInput.value); symbolInput.value = ''"
          >
        </div>
        <small class="hint">Premi Invio per aggiungere. Lascia vuoto per selezione automatica AI.</small>
      </div>

      <div class="form-group">
        <label>Descrizione Libera (AI Hint)</label>
        <textarea formControlName="free_text" placeholder="Es. 'Preferisco strategie trend following su Bitcoin con stop loss stretto'"></textarea>
        <div class="textarea-footer">
          <small class="hint">Spiega all'AI cosa cerchi per risultati più precisi.</small>
          <small class="counter" [class.warning]="(form.get('free_text')?.value?.length || 0) > 450">
            {{ form.get('free_text')?.value?.length || 0 }}/500
          </small>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" [disabled]="form.invalid" class="btn-primary">
          <span class="icon">✨</span> Genera Strategie con AI
        </button>
      </div>
    </form>
  `,
  styles: [`
    .request-form { display:flex; flex-direction:column; gap:20px; padding:24px; background: var(--bg-surface); border-radius: 12px; border: 1px solid var(--border-default); }
    .form-row { display: flex; gap: 16px; }
    .flex-1 { flex: 1; }
    .form-group { display:flex; flex-direction:column; gap:6px; }
    label { font-size:12px; font-weight: 600; color:var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
    
    .input-wrapper { position: relative; display: flex; align-items: center; }
    .prefix { position: absolute; left: 12px; color: var(--text-secondary); font-size: 14px; }
    .input-wrapper input { padding-left: 28px; width: 100%; }

    input, select, textarea { 
      background:var(--bg-card); border:1px solid var(--border-default); 
      color:var(--text-primary); padding:10px 12px; border-radius:6px; 
      font-size: 14px; transition: border-color 0.2s;
    }
    input:focus, select:focus, textarea:focus { border-color: var(--accent-primary); outline: none; }
    
    .risk-selector { display: flex; gap: 4px; background: var(--bg-card); padding: 4px; border-radius: 8px; border: 1px solid var(--border-default); }
    .risk-btn { 
      flex: 1; padding: 6px; border: none; border-radius: 6px; background: transparent; 
      color: var(--text-secondary); cursor: pointer; font-size: 12px; font-weight: 600;
      transition: all 0.2s;
    }
    .risk-btn.active { color: #000; }
    .risk-btn--low.active { background: #0ECB81; }
    .risk-btn--medium.active { background: #F0B90B; }
    .risk-btn--high.active { background: #F6465D; }

    .symbol-input-container { 
      display: flex; flex-wrap: wrap; gap: 8px; padding: 8px; 
      background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 6px; 
    }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; }
    .chip { 
      display: flex; align-items: center; gap: 4px; padding: 2px 8px; 
      background: rgba(240, 185, 11, 0.1); border: 1px solid var(--accent-primary); 
      color: var(--accent-primary); border-radius: 4px; font-size: 12px; font-family: monospace;
    }
    .remove-chip { background: none; border: none; color: var(--accent-primary); cursor: pointer; padding: 0; font-size: 16px; line-height: 1; }
    .symbol-input-container input { border: none; padding: 0; background: transparent; flex: 1; min-width: 150px; }

    textarea { height:100px; resize:none; }
    .textarea-footer { display: flex; justify-content: space-between; align-items: center; }
    .hint { font-size:11px; color:var(--text-secondary); font-style: italic; }
    .counter { font-size:10px; color:var(--text-secondary); }
    .counter.warning { color: var(--color-sell); font-weight: 600; }

    .btn-primary { 
      background:var(--accent-primary); color:#000; border:none; padding:14px; 
      border-radius:8px; font-weight:700; cursor:pointer; font-size: 15px;
      display: flex; align-items: center; justify-content: center; gap: 10px;
      transition: transform 0.1s, filter 0.2s;
    }
    .btn-primary:hover { filter: brightness(1.1); }
    .btn-primary:active { transform: scale(0.98); }
    .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
  `],
  // Per titlecase pipe
  host: { 'class': 'app-strategy-request-form' }
})
export class StrategyRequestFormComponent {
  private fb = inject(FormBuilder);
  requestSubmitted = output<StrategyRequest>();

  riskLevels: RiskLevel[] = ['low', 'medium', 'high'];
  selectedSymbols = signal<string[]>([]);

  form = this.fb.nonNullable.group({
    budget_eur: [100.0, [Validators.required, Validators.min(1)]],
    duration_days: [30, [Validators.required, Validators.min(1)]],
    risk_level: ['medium' as RiskLevel, [Validators.required]],
    asset_class: ['crypto' as AssetClass],
    free_text: ['', [Validators.maxLength(500)]],
    max_strategies: [5]
  });

  isRiskActive(level: string): boolean {
    return this.form.getRawValue().risk_level === level;
  }

  setRiskLevel(level: RiskLevel): void {
    this.form.patchValue({ risk_level: level });
  }

  addSymbol(value: string) {
    const symbol = value.trim().toUpperCase();
    if (symbol && !this.selectedSymbols().includes(symbol)) {
      this.selectedSymbols.update(s => [...s, symbol]);
    }
  }

  removeSymbol(symbol: string) {
    this.selectedSymbols.update(s => s.filter(x => x !== symbol));
  }

  onSubmit() {
    if (this.form.valid) {
      const rawValues = this.form.getRawValue();
      const request: StrategyRequest = {
        budget_eur: rawValues.budget_eur as number,
        duration_days: rawValues.duration_days as number,
        risk_level: rawValues.risk_level as RiskLevel,
        asset_class: rawValues.asset_class as AssetClass,
        free_text: rawValues.free_text as string,
        max_strategies: rawValues.max_strategies as number,
        symbols: this.selectedSymbols()
      };
      this.requestSubmitted.emit(request);
    }
  }
}


