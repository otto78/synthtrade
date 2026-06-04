/**
 * Scalping Dashboard Component - Main page
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { MarketIntelPanelComponent } from './market-intel-panel.component';
import { SignalScorecardComponent } from './signal-scorecard.component';
import { OpportunityFeedComponent } from './opportunity-feed.component';
import { SessionControlsComponent } from './session-controls.component';
import { PositionTickerComponent } from './position-ticker.component';
import { LiveChartComponent } from './live-chart.component';
import { StrategyPanelComponent } from './strategy-panel.component';
import { TradeLogComponent } from './trade-log.component';
import { PerformancePanelComponent } from './performance-panel.component';
import { SupervisorLogComponent } from './supervisor-log.component';
import { RiskControlsComponent } from './risk-controls.component';
import { ScalpingWsService } from '../services/scalping-ws.service';
import { Subscription } from 'rxjs';
import { NgFor, NgIf } from '@angular/common';

interface ErrorToast {
  id: number;
  message: string;
  code: string;
}

@Component({
  selector: 'app-scalping-dashboard',
  standalone: true,
  imports: [
    MarketIntelPanelComponent,
    SignalScorecardComponent,
    OpportunityFeedComponent,
    SessionControlsComponent,
    PositionTickerComponent,
    LiveChartComponent,
    StrategyPanelComponent,
    TradeLogComponent,
    PerformancePanelComponent,
    SupervisorLogComponent,
    RiskControlsComponent,
    NgFor,
    NgIf,
  ],
  template: `
    <div class="scalping-dashboard">
      <!-- Error Toast Notifications -->
      <div class="error-toasts" *ngIf="errorToasts.length > 0">
        <div class="error-toast" *ngFor="let toast of errorToasts" [attr.data-id]="toast.id">
          <span class="error-icon">⚠️</span>
          <span class="error-msg">{{ toast.message }}</span>
          <button class="dismiss-btn" (click)="dismissToast(toast.id)">✕</button>
        </div>
      </div>

      <div class="dashboard-grid">
        <app-session-controls class="card"></app-session-controls>
        <app-position-ticker class="card"></app-position-ticker>
        <app-live-chart class="card chart-card"></app-live-chart>
        <app-strategy-panel class="card"></app-strategy-panel>
        <app-trade-log class="card"></app-trade-log>
        <app-performance-panel class="card"></app-performance-panel>
        <app-supervisor-log class="card"></app-supervisor-log>
        <app-risk-controls class="card"></app-risk-controls>
        <app-market-intel-panel class="card"></app-market-intel-panel>
        <app-signal-scorecard class="card"></app-signal-scorecard>
        <app-opportunity-feed class="card"></app-opportunity-feed>
      </div>
    </div>
  `,
  styles: [`
    .scalping-dashboard { padding: 20px; }
    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .card { background: var(--bg-surface, #161B22); border: 1px solid var(--border-default, rgba(234,236,239,0.1)); border-radius: 8px; }
    .chart-card { grid-column: span 2; }

    .error-toasts {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }
    .error-toast {
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(239, 83, 80, 0.15);
      border: 1px solid rgba(239, 83, 80, 0.5);
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 13px;
      color: #ef9a9a;
      animation: slideIn 0.2s ease;
    }
    .error-icon { font-size: 15px; flex-shrink: 0; }
    .error-msg { flex: 1; line-height: 1.4; }
    .dismiss-btn {
      background: none;
      border: none;
      color: rgba(239,83,80,0.7);
      cursor: pointer;
      font-size: 14px;
      padding: 0 4px;
      flex-shrink: 0;
      line-height: 1;
    }
    .dismiss-btn:hover { color: #ef5350; }
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(-6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `],
})
export class ScalpingDashboardComponent implements OnInit, OnDestroy {
  errorToasts: ErrorToast[] = [];
  private _toastCounter = 0;
  private _sub = new Subscription();

  constructor(private wsService: ScalpingWsService) {}

  ngOnInit(): void {
    this.wsService.connect();

    this._sub.add(
      this.wsService.error$.subscribe((err) => {
        this._showError(err.message, err.code);
      })
    );
  }

  ngOnDestroy(): void {
    this.wsService.disconnect();
    this._sub.unsubscribe();
  }

  dismissToast(id: number): void {
    this.errorToasts = this.errorToasts.filter(t => t.id !== id);
  }

  private _showError(message: string, code: string): void {
    const id = ++this._toastCounter;
    this.errorToasts.push({ id, message, code });
    // Auto-dismiss after 8 seconds
    setTimeout(() => this.dismissToast(id), 8000);
  }
}