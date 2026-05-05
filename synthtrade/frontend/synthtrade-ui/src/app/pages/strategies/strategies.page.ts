import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { StrategyService } from '../../core/services/strategy.service';
import { Strategy, StrategyStatus } from '../../core/models/strategy.model';
import { BadgeStatusComponent } from '../../shared/components/badge-status/badge-status.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { NgClass } from '@angular/common';

type Tab = 'ALL' | 'ACTIVE' | 'PENDING';

@Component({
  selector: 'app-strategies',
  standalone: true,
  imports: [BadgeStatusComponent, ConfirmDialogComponent, EmptyStateComponent, NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="strategies">
      <div class="tabs">
        @for (tab of tabs; track tab) {
          <button class="tab" [ngClass]="{ 'tab--active': activeTab() === tab }" (click)="activeTab.set(tab)">
            {{ tab }}
          </button>
        }
      </div>

      @if (filtered().length === 0 && !loading()) {
        <app-empty-state message="Nessuna strategia trovata" />
      } @else {
        <div class="strategy-list">
          @for (s of filtered(); track s.id) {
            <div class="strategy-row">
              <div class="strategy-info">
                <span class="strategy-title">{{ s.title }}</span>
                <span class="strategy-pair">{{ s.pair }} · {{ s.timeframe }}</span>
              </div>
              <app-badge-status [status]="s.status" />
              <div class="strategy-actions">
                @if (s.status === 'PENDING') {
                  <button class="btn-approve" (click)="approve(s)">Approva</button>
                }
                <button class="btn-reject" (click)="confirmReject(s)">Rifiuta</button>
              </div>
            </div>
          }
        </div>
      }

      <app-confirm-dialog
        [visible]="!!pendingReject()"
        message="Rifiutare questa strategia?"
        (confirmed)="doReject()"
        (cancelled)="pendingReject.set(null)"
      />
    </div>
  `,
  styles: [`
    .tabs { display: flex; gap: 8px; margin-bottom: 16px; }
    .tab { background: none; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; }
    .tab--active { border-color: var(--accent-primary); color: var(--accent-primary); }
    .strategy-list { display: flex; flex-direction: column; gap: 8px; }
    .strategy-row { display: flex; align-items: center; gap: 16px; padding: 12px 16px; background: var(--bg-surface); border-radius: 8px; border: 1px solid var(--border-default); }
    .strategy-info { flex: 1; }
    .strategy-title { display: block; font-size: 14px; color: var(--text-primary); }
    .strategy-pair { font-size: 12px; color: var(--text-secondary); font-family: monospace; }
    .strategy-actions { display: flex; gap: 8px; }
    .btn-approve { background: rgba(14,203,129,0.1); color: var(--color-buy); border: 1px solid var(--color-buy); padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
    .btn-reject  { background: rgba(246,70,93,0.1);  color: var(--color-sell); border: 1px solid var(--color-sell); padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  `]
})
export class StrategiesPage implements OnInit {
  private strategyService = inject(StrategyService);

  readonly tabs: Tab[] = ['ALL', 'ACTIVE', 'PENDING'];
  strategies = signal<Strategy[]>([]);
  activeTab = signal<Tab>('ALL');
  loading = signal(true);
  pendingReject = signal<Strategy | null>(null);

  filtered = computed(() => {
    const tab = this.activeTab();
    const all = this.strategies();
    if (tab === 'ALL') return all;
    return all.filter(s => s.status === (tab as StrategyStatus));
  });

  ngOnInit(): void {
    this.strategyService.getStrategies().subscribe({
      next: (data) => { this.strategies.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  approve(s: Strategy): void {
    this.strategyService.approve(s.id).subscribe(res => {
      this.strategies.update(list => list.map(x => x.id === s.id ? { ...x, status: res.status as StrategyStatus } : x));
    });
  }

  confirmReject(s: Strategy): void {
    this.pendingReject.set(s);
  }

  doReject(): void {
    const s = this.pendingReject();
    if (!s) return;
    this.strategyService.reject(s.id).subscribe(res => {
      this.strategies.update(list => list.map(x => x.id === s.id ? { ...x, status: res.status as StrategyStatus } : x));
      this.pendingReject.set(null);
    });
  }
}
