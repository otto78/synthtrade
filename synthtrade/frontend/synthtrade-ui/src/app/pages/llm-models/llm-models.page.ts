import { ChangeDetectionStrategy, Component, OnInit, OnDestroy, inject, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { LLMModelsService } from '../../core/services/llm-models.service';
import { LLMModelsPayload } from '../../core/models/llm-models.model';

interface ModelEntry {
  current: string;
  newValue: string;
  status: 'checking' | 'online' | 'offline' | 'unknown';
}

@Component({
  selector: 'app-llm-models',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="llm-page">
      <h2>Configurazione Modelli LLM</h2>
      <form (ngSubmit)="save()" #modelForm="ngForm">
        <h3>Cascade Modelli</h3>
        <p class="hint">Sostituisci un modello inserendo il nuovo nome nel campo. Lascia vuoto per mantenerlo invariato.</p>
        <div class="model-list">
          <div class="model-row" *ngFor="let entry of entries; let i = index; trackBy: trackByIndex">
            <div class="row-label">
              <span class="status-dot" [class.online]="entry.status === 'online'" [class.offline]="entry.status === 'offline'" [class.checking]="entry.status === 'checking'"></span>
              <label [for]="'model-' + i">{{ entry.current }}</label>
            </div>
            <div class="row-input">
              <input
                [id]="'model-' + i"
                [(ngModel)]="entry.newValue"
                [name]="'model-' + i"
                class="input"
                placeholder="Nuovo modello (vuoto = invariato)"
              />
              <button type="button" class="btn-remove" (click)="removeEntry(i)" title="Rimuovi modello">&times;</button>
            </div>
          </div>
        </div>
        <button type="button" class="btn-add" (click)="addEntry()">+ Aggiungi modello</button>

        <div class="field">
          <label for="fallback">Modello Fallback</label>
          <input id="fallback" [(ngModel)]="fallback" name="fallback" class="input" placeholder="Nuovo fallback (vuoto = invariato)" />
        </div>

        <div class="actions">
          <button type="submit" class="btn-save" [disabled]="loading || checking">Salva</button>
          <span *ngIf="message" class="msg" [class.error]="isError">{{ message }}</span>
        </div>
      </form>
    </div>
  `,
  styles: [`
    .llm-page { max-width: 680px; margin: 20px auto; padding: 0 16px; }
    h2 { margin-bottom: 4px; }
    h3 { margin: 20px 0 4px; font-size: 1.1rem; }
    .hint { color: var(--text-secondary, #666); font-size: 0.85rem; margin: 0 0 16px; }
    .field { margin-bottom: 20px; }
    label { display: block; margin-bottom: 4px; font-weight: 600; font-size: 0.9rem; color: var(--text-secondary, #888); }
    .input {
      width: 100%; padding: 8px;
      border: 1px solid var(--border-default, #444);
      border-radius: 4px; box-sizing: border-box;
      background: var(--bg-input, #1e1e2e);
      color: var(--text-primary, #e0e0e0);
    }
    .input:focus { border-color: var(--accent-primary, #0066cc); outline: none; }
    .model-list { margin-bottom: 8px; }
    .model-row { margin-bottom: 10px; }
    .row-label { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
    .row-label label { margin-bottom: 0; }
    .status-dot {
      width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0;
    }
    .status-dot.online { background: #0ECB81; box-shadow: 0 0 6px rgba(14,203,129,0.4); }
    .status-dot.offline { background: #F6465D; box-shadow: 0 0 6px rgba(246,70,93,0.4); }
    .status-dot.checking { background: #F0B90B; animation: pulse 1s infinite; }
    .row-input { display: flex; gap: 6px; align-items: center; }
    .row-input .input { flex: 1; }
    .btn-remove {
      background: none; border: 1px solid var(--border-default, #444); border-radius: 4px;
      font-size: 1.2rem; cursor: pointer; padding: 4px 10px; line-height: 1;
      color: var(--text-danger, #e55);
    }
    .btn-add {
      background: none; border: 1px dashed var(--border-default, #555); border-radius: 4px;
      padding: 6px 16px; cursor: pointer; margin-bottom: 20px; width: 100%;
      color: var(--accent-primary, #6af);
    }
    .btn-save { padding: 8px 24px; background: var(--accent-primary, #0066cc); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
    .btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
    .actions { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
    .msg { font-size: 0.9rem; }
    .msg.error { color: var(--text-danger, #e55); }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LLMModelsPage implements OnInit, OnDestroy {
  private service = inject(LLMModelsService);
  private cdr = inject(ChangeDetectorRef);
  private sub = new Subscription();
  entries: ModelEntry[] = [];
  fallback = '';
  fallbackCurrent = '';
  loading = false;
  checking = false;
  message = '';
  isError = false;

  ngOnInit(): void {
    this.load();
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  trackByIndex(index: number): number {
    return index;
  }

  load() {
    this.loading = true;
    this.sub.add(
      this.service.getModels().subscribe({
        next: (data: LLMModelsPayload) => {
          this.entries = data.cascade.length > 0
            ? data.cascade.map((m: string) => ({ current: m, newValue: '', status: 'checking' as const }))
            : [{ current: '', newValue: '', status: 'unknown' as const }];
          this.fallback = data.fallback;
          this.fallbackCurrent = data.fallback;
          this.loading = false;
          this.cdr.markForCheck();
          // Kick off async health checks after models are loaded
          this.runHealthCheck();
        },
        error: () => {
          this.message = 'Errore nel caricamento dei modelli';
          this.isError = true;
          this.loading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  runHealthCheck(includeFallback = false) {
    this.checking = true;
    this.sub.add(
      this.service.checkModels(undefined, includeFallback).subscribe({
        next: (res) => {
          const statusMap = new Map<string, 'online' | 'offline'>();
          for (const check of res.checks) {
            statusMap.set(check.model, check.status);
          }
          for (const entry of this.entries) {
            entry.status = statusMap.get(entry.current) || 'unknown';
          }
          this.checking = false;
          this.cdr.markForCheck();
        },
        error: () => {
          for (const entry of this.entries) {
            entry.status = 'unknown';
          }
          this.checking = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  addEntry(): void {
    this.entries.push({ current: 'Nuovo modello', newValue: '', status: 'unknown' });
  }

  removeEntry(index: number): void {
    if (this.entries.length > 1) {
      this.entries.splice(index, 1);
    }
  }

  save() {
    this.loading = true;
    this.message = '';
    this.isError = false;

    const cascadeArray = this.entries.map(e => (e.newValue.trim() || e.current).trim()).filter(Boolean);
    if (cascadeArray.length === 0) {
      this.message = 'Inserisci almeno un modello nella cascade';
      this.isError = true;
      this.loading = false;
      this.cdr.markForCheck();
      return;
    }
    const fallbackVal = this.fallback.trim() || this.fallbackCurrent;
    if (!fallbackVal) {
      this.message = 'Inserisci un modello di fallback';
      this.isError = true;
      this.loading = false;
      this.cdr.markForCheck();
      return;
    }

    // TASK-XXX: Skip API call if nothing actually changed
    const originalCascade = this.entries.map(e => e.current).filter(Boolean);
    const cascadeChanged = JSON.stringify(cascadeArray) !== JSON.stringify(originalCascade);
    const fallbackChanged = fallbackVal !== this.fallbackCurrent;
    if (!cascadeChanged && !fallbackChanged) {
      this.message = 'Nessuna modifica rilevata';
      this.loading = false;
      this.cdr.markForCheck();
      return;
    }

    // Pre-save validation: ping the *proposed* models, not the DB ones
    const allModels = [...cascadeArray];
    if (fallbackVal && !allModels.includes(fallbackVal)) {
      allModels.push(fallbackVal);
    }
    this.checking = true;
    this.sub.add(
      this.service.checkModels(allModels).subscribe({
        next: (res) => {
          this.checking = false;
          const offlineModels = res.checks.filter(c => c.status === 'offline').map(c => c.model);
          if (offlineModels.length > 0) {
            this.message = `Salvataggio bloccato — modelli offline: ${offlineModels.join(', ')}`;
            this.isError = true;
            this.loading = false;
            this.cdr.markForCheck();
            return;
          }
          // All good — proceed with save
          this.doSetModels(cascadeArray, fallbackVal);
        },
        error: () => {
          this.checking = false;
          this.message = 'Impossibile verificare lo stato dei modelli. Riprova.';
          this.isError = true;
          this.loading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }
  private doSetModels(cascadeArray: string[], fallbackVal: string) {
    this.sub.add(
      this.service.setModels({ cascade: cascadeArray, fallback: fallbackVal }).subscribe({
        next: () => {
          this.message = 'Salvataggio completato';
          this.entries = cascadeArray.map(m => ({ current: m, newValue: '', status: 'checking' as const }));
          this.fallbackCurrent = fallbackVal;
          this.fallback = '';
          this.loading = false;
          this.cdr.markForCheck();
          // Re-run health check to refresh indicators
          this.runHealthCheck();
        },
        error: () => {
          this.message = 'Errore nel salvataggio';
          this.isError = true;
          this.loading = false;
          this.cdr.markForCheck();
          // Trigger re-check — maybe models changed externally or auth expired
          this.runHealthCheck();
        },
      })
    );
  }
}
