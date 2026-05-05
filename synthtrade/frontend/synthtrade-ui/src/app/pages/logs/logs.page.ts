import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { Subscription } from 'rxjs';
import { LogService } from '../../core/services/log.service';
import { WsService } from '../../core/services/ws.service';
import { WsMessageType } from '../../core/models/ws-message.model';
import { OperationLog, LogFilters, LogLevel } from '../../core/models/log.model';
import { BadgeStatusComponent } from '../../shared/components/badge-status/badge-status.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';

const PAGE_SIZE = 50;

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [NgClass, BadgeStatusComponent, RelativeTimePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="logs-page">
      <div class="logs-toolbar">
        <select class="filter-level" (change)="onFilterChange($event)">
          <option value="">Tutti</option>
          @for (level of levels; track level) {
            <option [value]="level">{{ level }}</option>
          }
        </select>
      </div>

      <div class="log-list">
        @for (log of logs(); track log.id) {
          <div class="log-row">
            <span class="log-time">{{ log.created_at | relativeTime }}</span>
            <app-badge-status [status]="log.action" />
            <span class="log-reason">{{ log.reason ?? '—' }}</span>
            @if (log.price) {
              <span class="log-price">{{ log.price }}</span>
            }
          </div>
        }
      </div>

      <div class="pagination">
        <button class="btn-prev" [disabled]="offset() === 0" (click)="prevPage()">‹ Prev</button>
        <span class="page-info">{{ offset() / pageSize + 1 }}</span>
        <button class="btn-next" (click)="nextPage()">Next ›</button>
      </div>
    </div>
  `,
  styles: [`
    .logs-toolbar { margin-bottom: 16px; }
    select { background: var(--bg-elevated); border: 1px solid var(--border-default); color: var(--text-primary); padding: 6px 12px; border-radius: 4px; font-size: 13px; }
    .log-list { display: flex; flex-direction: column; gap: 4px; }
    .log-row { display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: var(--bg-surface); border-radius: 4px; font-size: 13px; }
    .log-time { color: var(--text-muted); font-family: monospace; font-size: 11px; min-width: 60px; }
    .log-reason { flex: 1; color: var(--text-secondary); }
    .log-price { font-family: monospace; color: var(--text-primary); }
    .pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; justify-content: flex-end; }
    .btn-prev, .btn-next { background: none; border: 1px solid var(--border-default); color: var(--text-secondary); padding: 4px 12px; border-radius: 4px; cursor: pointer; }
    .btn-prev:disabled { opacity: 0.3; cursor: not-allowed; }
    .page-info { color: var(--text-muted); font-size: 13px; }
  `]
})
export class LogsPage implements OnInit, OnDestroy {
  private logService = inject(LogService);
  private wsService = inject(WsService);
  private sub = new Subscription();

  readonly levels: LogLevel[] = ['BUY', 'SELL', 'SKIP', 'BLOCK', 'ERROR'];
  readonly pageSize = PAGE_SIZE;

  logs = signal<OperationLog[]>([]);
  offset = signal(0);
  private activeFilter: LogLevel | undefined = undefined;

  ngOnInit(): void {
    this.load();
    this.sub.add(
      this.wsService.on<OperationLog>(WsMessageType.NewLog).subscribe(msg => {
        if (msg.payload) this.logs.update(list => [msg.payload!, ...list]);
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }

  onFilterChange(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as LogLevel | '';
    this.activeFilter = val || undefined;
    this.offset.set(0);
    this.load();
  }

  nextPage(): void {
    this.offset.update(o => o + PAGE_SIZE);
    this.load();
  }

  prevPage(): void {
    this.offset.update(o => Math.max(0, o - PAGE_SIZE));
    this.load();
  }

  private load(): void {
    const filters: LogFilters = { limit: PAGE_SIZE, offset: this.offset() };
    if (this.activeFilter) filters.action = this.activeFilter;
    this.logService.getLogs(filters).subscribe(data => this.logs.set(data));
  }
}
