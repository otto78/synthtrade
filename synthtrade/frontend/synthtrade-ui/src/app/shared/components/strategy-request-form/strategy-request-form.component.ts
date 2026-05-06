import { ChangeDetectionStrategy, Component, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { StrategyRequest, RiskLevel, AssetClass } from '../../../core/models/strategy.model';

@Component({
  selector: 'app-strategy-request-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" class="request-form">
      <div class="form-group">
        <label>Budget (EUR)</label>
        <input type="number" formControlName="budget_eur" placeholder="Es. 100">
      </div>

      <div class="form-group">
        <label>Durata (Giorni)</label>
        <input type="number" formControlName="duration_days" placeholder="Es. 30">
      </div>

      <div class="form-group">
        <label>Livello di Rischio</label>
        <select formControlName="risk_level">
          <option value="low">Basso</option>
          <option value="medium">Medio</option>
          <option value="high">Alto</option>
        </select>
      </div>

      <div class="form-group">
        <label>Descrizione Libera (AI Hint)</label>
        <textarea formControlName="free_text" placeholder="Es. 'Preferisco strategie trend following su Bitcoin'"></textarea>
        <small class="counter">{{ form.get('free_text')?.value?.length || 0 }}/500</small>
      </div>

      <div class="form-actions">
        <button type="submit" [disabled]="form.invalid" class="btn-primary">Genera Strategie</button>
      </div>
    </form>
  `,
  styles: [`
    .request-form { display:flex; flex-direction:column; gap:16px; padding:16px; }
    .form-group { display:flex; flex-direction:column; gap:4px; }
    label { font-size:12px; color:var(--text-secondary,#848E9C); }
    input, select, textarea { 
      background:var(--bg-card,#1E2329); border:1px solid var(--border-default,#30363D); 
      color:var(--text-primary,#EAECEF); padding:8px; border-radius:4px; 
    }
    textarea { height:80px; resize:none; }
    .counter { align-self:flex-end; font-size:10px; color:var(--text-secondary); }
    .btn-primary { 
      background:var(--color-buy,#0ECB81); color:#000; border:none; padding:10px; 
      border-radius:4px; font-weight:600; cursor:pointer; 
    }
    .btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
  `]
})
export class StrategyRequestFormComponent {
  private fb = new FormBuilder();
  requestSubmitted = output<StrategyRequest>();

  form = this.fb.group({
    budget_eur: [100.0, [Validators.required, Validators.min(1)]],
    duration_days: [30, [Validators.required, Validators.min(1)]],
    risk_level: ['medium' as RiskLevel, Validators.required],
    asset_class: ['crypto' as AssetClass],
    free_text: ['', Validators.maxLength(500)],
    max_strategies: [5]
  });

  onSubmit() {
    if (this.form.valid) {
      this.requestSubmitted.emit(this.form.value as StrategyRequest);
    }
  }
}
