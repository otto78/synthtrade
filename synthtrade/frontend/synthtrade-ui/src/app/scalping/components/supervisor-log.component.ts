/**
 * Supervisor Log Component
 * Displays AI decisions log
 */

import { Component, OnInit, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { DatePipe, DecimalPipe, NgClass, NgForOf, NgIf } from '@angular/common';
import { ScalpingWsService, SupervisorDecision } from '../services/scalping-ws.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-supervisor-log',
  standalone: true,
  imports: [DatePipe, DecimalPipe, NgClass, NgForOf, NgIf],
  template: `
    <div class="supervisor-log">
      <span class="panel-title">AI Supervisor Log</span>

      <div *ngIf="!decisions.length" class="empty">No AI decisions yet</div>

      <div class="decisions-list">
        <div class="decision-item" *ngFor="let dec of decisions">
          <div class="header">
            <span class="action" [ngClass]="dec.action.toLowerCase()">{{ dec.action.replace('_', ' ') }}</span>
            <span class="time">{{ (dec.timestamp || dec.decided_at) | date:'HH:mm:ss' }}</span>
          </div>
          <div class="reason">{{ dec.reason }}</div>
          <div class="details" *ngIf="dec.new_strategy || dec.new_params">
             <span *ngIf="dec.new_strategy">Target: {{ dec.new_strategy }}</span>
          </div>
          <div class="confidence">Confidence: {{ dec.confidence * 100 | number:'1.0-0' }}%</div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .supervisor-log { padding: 12px; max-height: 400px; overflow-y: auto; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .empty { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    .decisions-list { font-size: 12px; }
    .decision-item { padding: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; margin-bottom: 8px; }
    .header { display: flex; justify-content: space-between; margin-bottom: 6px; align-items: center; }
    .action { font-weight: 700; padding: 2px 8px; border-radius: 4px; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Mapping backend strings to CSS colors */
    .action.update_params, .action.modify_params { background: rgba(240, 185, 11, 0.2); color: #F0B90B; border: 1px solid rgba(240, 185, 11, 0.3); }
    .action.change_strategy { background: rgba(255, 183, 77, 0.2); color: #ffb74d; border: 1px solid rgba(255, 183, 77, 0.3); }
    .action.pause_trading, .action.pause { background: rgba(239, 83, 80, 0.2); color: #ef5350; border: 1px solid rgba(239, 83, 80, 0.3); }
    .action.resume_trading, .action.resume { background: rgba(38, 166, 154, 0.2); color: #26a69a; border: 1px solid rgba(38, 166, 154, 0.3); }
    .action.no_action { background: rgba(132, 142, 156, 0.1); color: #848E9C; border: 1px solid rgba(132, 142, 156, 0.2); }

    .time { font-size: 10px; color: var(--text-secondary); font-family: monospace; }
    .reason { font-size: 11px; color: var(--text-primary); margin-bottom: 6px; line-height: 1.4; }
    .details { font-size: 10px; color: var(--accent-primary); margin-bottom: 4px; font-weight: 600; }
    .confidence { font-size: 10px; color: var(--text-secondary); opacity: 0.8; }
  `],
})
export class SupervisorLogComponent implements OnInit, OnDestroy {
  decisions: SupervisorDecision[] = [];
  private sub = new Subscription();

  constructor(
    private ws: ScalpingWsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.sub.add(
      this.ws.supervisorDecision$.subscribe((decision: SupervisorDecision | null) => {
        if (!decision) return;
        console.log('[SupervisorLog] New decision received:', decision);
        this.decisions = [decision, ...this.decisions.slice(0, 49)];
        // Force manual change detection because WS event is asynchronous
        this.cdr.detectChanges();
      })
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }
}