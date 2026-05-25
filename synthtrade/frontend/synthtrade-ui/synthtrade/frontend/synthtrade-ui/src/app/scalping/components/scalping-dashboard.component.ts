/**
 * Scalping Dashboard Component - Main page
 */

import { Component } from '@angular/core';
import { MarketIntelPanelComponent } from './market-intel-panel.component';
import { SignalScorecardComponent } from './signal-scorecard.component';
import { OpportunityFeedComponent } from './opportunity-feed.component';
import { SessionControlsComponent } from './session-controls.component';

@Component({
  selector: 'app-scalping-dashboard',
  standalone: true,
  imports: [
    MarketIntelPanelComponent,
    SignalScorecardComponent,
    OpportunityFeedComponent,
    SessionControlsComponent,
  ],
  template: `
    <div class="scalping-dashboard">
      <h1>Scalping Dashboard v2.0</h1>
      <p>Signal Intelligence Engine</p>

      <div class="dashboard-grid">
        <app-market-intel-panel class="card"></app-market-intel-panel>
        <app-signal-scorecard class="card"></app-signal-scorecard>
        <app-opportunity-feed class="card"></app-opportunity-feed>
        <app-session-controls class="card"></app-session-controls>
      </div>
    </div>
  `,
  styles: [`
    .scalping-dashboard { padding: 20px; }
    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 20px; }
    .card { background: var(--bg-surface, #161B22); border: 1px solid var(--border-default, rgba(234,236,239,0.1)); border-radius: 8px; padding: 16px; }
    h1 { margin: 0; color: var(--text-primary, #EAECEF); }
    p { margin: 4px 0 0 0; color: var(--text-secondary, #848E9C); }
  `],
})
export class ScalpingDashboardComponent {}