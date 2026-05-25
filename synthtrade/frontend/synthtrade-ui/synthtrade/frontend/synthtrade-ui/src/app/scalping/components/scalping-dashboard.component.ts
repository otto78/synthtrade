/**
 * Scalping Dashboard Component - Main page
 */

import { Component } from '@angular/core';

@Component({
  selector: 'app-scalping-dashboard',
  standalone: true,
  template: `
    <div class="scalping-dashboard">
      <h1>Scalping Dashboard v2.0</h1>
      <p>Signal Intelligence Engine</p>

      <div class="dashboard-grid">
        <!-- Market Intelligence Panel -->
        <div class="card">
          <h2>Market Intelligence</h2>
          <p>Funding Rate, OI, CVD, Fear & Greed</p>
        </div>

        <!-- Signal Scorecard -->
        <div class="card">
          <h2>Signal Score</h2>
          <p>0-100 aggregate score</p>
        </div>

        <!-- Opportunity Feed -->
        <div class="card">
          <h2>Opportunities</h2>
          <p>AI-classified trading alerts</p>
        </div>

        <!-- Session Controls -->
        <div class="card">
          <h2>Session</h2>
          <p>Start/Stop/Paper Mode</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .scalping-dashboard {
      padding: 20px;
    }
    .dashboard-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }
    .card {
      background: var(--bg-surface, #161B22);
      border: 1px solid var(--border-default, rgba(234,236,239,0.1));
      border-radius: 8px;
      padding: 16px;
    }
    h2 {
      margin: 0 0 8px 0;
      color: var(--text-primary, #EAECEF);
    }
    p {
      margin: 0;
      color: var(--text-secondary, #848E9C);
    }
  `],
})
export class ScalpingDashboardComponent {}