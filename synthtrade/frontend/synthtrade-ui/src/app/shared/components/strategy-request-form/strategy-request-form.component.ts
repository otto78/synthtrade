import { ChangeDetectionStrategy, Component, output, signal, inject, computed } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { StrategyRequest, RiskLevel, AssetClass, AllocationItem } from '../../../core/models/strategy.model';
import { TitleCasePipe, DecimalPipe } from '@angular/common';

@Component({
  selector: 'app-strategy-request-form',
  standalone: true,
  imports: [ReactiveFormsModule, TitleCasePipe, DecimalPipe],
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
        <label>Modalità Selezione Crypto</label>
        <div class="mode-selector">
          <button
            type="button"
            class="mode-btn"
            [class.active]="!useAllocation()"
            (click)="useAllocation.set(false)"
          >
            🤖 AI Automatica
          </button>
          <button
            type="button"
            class="mode-btn"
            [class.active]="useAllocation()"
            (click)="useAllocation.set(true)"
          >
            🎯 Allocation Manuale
          </button>
        </div>
      </div>

      @if (!useAllocation()) {
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
      }

      @if (useAllocation()) {
        <div class="form-group">
          <label>Allocation Multi-Crypto</label>
          <div class="allocation-container">
            @for (item of allocation(); track $index) {
              <div class="allocation-row">
                <input
                  type="text"
                  class="alloc-symbol"
                  [value]="item.symbol"
                  (input)="updateAllocationSymbol($index, $any($event.target).value)"
                  placeholder="BTCUSDT"
                >
                <div class="alloc-slider-group">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    [value]="item.percentage"
                    (input)="updateAllocationPercentage($index, +$any($event.target).value)"
                    class="alloc-slider"
                  >
                  <span class="alloc-value">{{ item.percentage | number:'1.0-0' }}%</span>
                </div>
                <button
                  type="button"
                  class="btn-remove-alloc"
                  (click)="removeAllocation($index)"
                >
                  ×
                </button>
              </div>
            }
            <button
              type="button"
              class="btn-add-alloc"
              (click)="addAllocation()"
            >
              + Aggiungi Crypto
            </button>
            <div class="allocation-summary" [class.valid]="allocationSumValid()" [class.invalid]="!allocationSumValid()">
              <span class="sum-label">Totale Allocation:</span>
              <span class="sum-value">{{ allocationSum() | number:'1.0-0' }}%</span>
              @if (!allocationSumValid() && allocation().length > 0) {
                <span class="sum-error">⚠️ Deve essere 100%</span>
              }
            </div>
          </div>
          <small class="hint">Specifica le crypto e la percentuale di budget per ognuna. Il totale deve essere 100%.</small>
        </div>
      }

      <div class="form-group">
        <label>Nome Personalizzato (opzionale)</label>
        <input formControlName="custom_name" placeholder="Es. 'Toro Scatenato', 'Moon Landing'..." maxlength="100">
        <small class="hint">Dai un nome simpatico alla tua strategia per riconoscerla facilmente.</small>
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
        <button type="submit" [disabled]="form.invalid || (useAllocation() && allocation().length > 0 && !allocationSumValid())" class="btn-primary">
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

    .form-actions { display: flex; justify-content: center; }
    .btn-primary { 
      background:var(--accent-primary); color:#000; border:none; padding:14px; 
      border-radius:8px; font-weight:700; cursor:pointer; font-size: 15px;
      display: flex; align-items: center; justify-content: center; gap: 10px;
      width: 100%; transition: transform 0.1s, filter 0.2s;
    }
    .btn-primary:hover { filter: brightness(1.1); }
    .btn-primary:active { transform: scale(0.98); }
    .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }

    .mode-selector { display: flex; gap: 8px; }
    .mode-btn {
      flex: 1; padding: 10px; border: 1px solid var(--border-default); border-radius: 6px;
      background: var(--bg-card); color: var(--text-secondary); cursor: pointer;
      font-size: 14px; font-weight: 600; transition: all 0.2s;
    }
    .mode-btn.active {
      background: rgba(240, 185, 11, 0.1); border-color: var(--accent-primary);
      color: var(--accent-primary);
    }

    .allocation-container {
      display: flex; flex-direction: column; gap: 12px;
      background: var(--bg-card); padding: 16px; border: 1px solid var(--border-default); border-radius: 8px;
    }
    .allocation-row {
      display: grid; grid-template-columns: 140px 1fr 40px; gap: 12px; align-items: center;
    }
    .alloc-symbol {
      background: var(--bg-surface); border: 1px solid var(--border-default);
      color: var(--text-primary); padding: 8px 10px; border-radius: 6px;
      font-size: 13px; font-family: monospace; text-transform: uppercase;
    }
    .alloc-slider-group { display: flex; align-items: center; gap: 12px; }
    .alloc-slider {
      flex: 1; height: 6px; border-radius: 3px;
      background: var(--bg-surface); outline: none; -webkit-appearance: none;
    }
    .alloc-slider::-webkit-slider-thumb {
      -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
      background: var(--accent-primary); cursor: pointer;
    }
    .alloc-slider::-moz-range-thumb {
      width: 16px; height: 16px; border-radius: 50%;
      background: var(--accent-primary); cursor: pointer; border: none;
    }
    .alloc-value {
      font-size: 13px; font-weight: 700; color: var(--text-primary);
      font-family: monospace; min-width: 45px; text-align: right;
    }
    .btn-remove-alloc {
      background: rgba(246, 70, 93, 0.1); border: 1px solid var(--color-sell);
      color: var(--color-sell); width: 32px; height: 32px; border-radius: 6px;
      cursor: pointer; font-size: 18px; line-height: 1;
    }
    .btn-add-alloc {
      background: transparent; border: 1px dashed var(--border-default);
      color: var(--text-secondary); padding: 10px; border-radius: 6px;
      cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s;
    }
    .btn-add-alloc:hover { border-color: var(--accent-primary); color: var(--accent-primary); }

    .allocation-summary {
      display: flex; align-items: center; gap: 12px; padding: 12px;
      background: var(--bg-surface); border-radius: 6px; margin-top: 8px;
    }
    .sum-label { font-size: 12px; color: var(--text-secondary); font-weight: 600; }
    .sum-value { font-size: 16px; font-weight: 700; font-family: monospace; }
    .allocation-summary.valid .sum-value { color: var(--color-buy); }
    .allocation-summary.invalid .sum-value { color: var(--color-sell); }
    .sum-error { font-size: 11px; color: var(--color-sell); font-weight: 600; margin-left: auto; }
  `],
  // Per titlecase pipe
  host: { 'class': 'app-strategy-request-form' }
})
export class StrategyRequestFormComponent {
  private fb = inject(FormBuilder);
  requestSubmitted = output<StrategyRequest>();

  riskLevels: RiskLevel[] = ['low', 'medium', 'high'];
  selectedSymbols = signal<string[]>([]);
  useAllocation = signal<boolean>(false);
  allocation = signal<AllocationItem[]>([]);

  allocationSum = computed(() =>
    this.allocation().reduce((sum, item) => sum + item.percentage, 0)
  );
  allocationSumValid = computed(() =>
    Math.abs(this.allocationSum() - 100) < 0.01
  );

  form = this.fb.nonNullable.group({
    budget_eur: [100.0, [Validators.required, Validators.min(1)]],
    duration_days: [30, [Validators.required, Validators.min(1)]],
    risk_level: ['medium' as RiskLevel, [Validators.required]],
    asset_class: ['crypto' as AssetClass],
    free_text: ['', [Validators.maxLength(500)]],
    max_strategies: [5],
    custom_name: ['', [Validators.maxLength(100)]]
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

  addAllocation() {
    this.allocation.update(alloc => [
      ...alloc,
      { symbol: '', percentage: 0 }
    ]);
  }

  removeAllocation(index: number) {
    this.allocation.update(alloc => alloc.filter((_, i) => i !== index));
  }

  updateAllocationSymbol(index: number, symbol: string) {
    this.allocation.update(alloc => {
      const updated = [...alloc];
      updated[index] = { ...updated[index], symbol: symbol.trim().toUpperCase() };
      return updated;
    });
  }

  updateAllocationPercentage(index: number, percentage: number) {
    this.allocation.update(alloc => {
      const updated = [...alloc];
      updated[index] = { ...updated[index], percentage };
      return updated;
    });
  }

  onSubmit() {
    if (this.form.valid) {
      // Validation: if using allocation, must sum to 100%
      if (this.useAllocation() && this.allocation().length > 0 && !this.allocationSumValid()) {
        return; // Don't submit if allocation is invalid
      }

      const rawValues = this.form.getRawValue();
      const request: StrategyRequest = {
        budget_eur: rawValues.budget_eur as number,
        duration_days: rawValues.duration_days as number,
        risk_level: rawValues.risk_level as RiskLevel,
        asset_class: rawValues.asset_class as AssetClass,
        free_text: rawValues.free_text as string,
        max_strategies: rawValues.max_strategies as number,
        custom_name: rawValues.custom_name as string || undefined
      };

      // Add allocation or symbols based on mode
      if (this.useAllocation() && this.allocation().length > 0) {
        request.allocation = this.allocation().filter(item => item.symbol.length > 0);
      } else {
        request.symbols = this.selectedSymbols();
      }

      this.requestSubmitted.emit(request);
    }
  }
}


