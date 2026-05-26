/**
 * Supervisor Log Component
 * Displays AI decisions log
 */

import { Component, OnInit } from '@angular/core';
import { DatePipe, DecimalPipe, NgClass, NgForOf, NgIf } from '@angular/common';
import { ScalpingWsService, SupervisorDecision } from '../services/scalping-ws.service';

@Component({
  selector: 'app-supervisor-log',
  standalone: true,
  imports: [DatePipe, DecimalPipe, NgClass, NgForOf, NgIf],
  template: `
    <div class="supervisor-log">
      <h3>AI Supervisor Log</h3>

      <div *ngIf="!decisions.length" class="empty">No AI decisions yet</div>

      <div class="decisions-list">
        <div class="decision-item" *ngFor="let dec of decisions">
          <div class="header">
            <span class="action" [ngClass]="dec.action.toLowerCase()">{{ dec.action }}</span>
            <span class="time">{{ dec.timestamp | date:'shortTime' }}</span>
          </div>
          <div class="reason">{{ dec.reason }}</div>
          <div class="confidence">Confidence: {{ dec.confidence * 100 | number:'1.0-0' }}%</div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .supervisor-log { padding: 12px; max-height: 300px; overflow-y: auto; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .empty { color: var(--text-secondary); font-size: 12px; padding: 8px; }
    .decisions-list { font-size: 12px; }
    .decision-item { padding: 8px; background: var(--bg-elevated); border-radius: 4px; margin-bottom: 8px; }
    .header { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .action { font-weight: 600; padding: 2px 6px; border-radius: 2px; font-size: 10px; }
    .action.modify_params { background: var(--accent-primary, #F0B90B); color: #000; }
    .action.change_strategy { background: var(--accent-warning, #ffb74d); color: #000; }
    .action.pause { background: var(--accent-danger, #ef5350); color: #fff; }
    .action.resume { background: var(--accent-success, #26a69a); color: #fff; }
    .reason { font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
    .confidence { font-size: 10px; color: var(--text-secondary); }
  `],
})
export class SupervisorLogComponent implements OnInit {
  decisions: SupervisorDecision[] = [];

  constructor(private ws: ScalpingWsService) {}

  ngOnInit(): void {
    this.ws.supervisorDecision$.subscribe(decision => {
      this.decisions = [decision, ...this.decisions.slice(0, 49)];
    });
  }
}