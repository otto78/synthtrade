/**
 * Market Intelligence Panel Component
 * Displays real-time market data
 */

import { Component, OnInit } from '@angular/core';
import { AsyncPipe, NgIf } from '@angular/common';
import { IntelligenceApiService } from '../services/intelligence-api.service';

@Component({
  selector: 'app-market-intel-panel',
  standalone: true,
  imports: [AsyncPipe, NgIf],
  template: `
    <div class="intel-panel">
      <h3>Market Intelligence</h3>

      <div class="intel-grid">
        <div class="intel-item">
          <span class="label">Funding Rate</span>
          <span class="value">{{ fundingRate }}%</span>
        </div>
        <div class="intel-item">
          <span class="label">Open Interest</span>
          <span class="value">{{ openInterest | number:'1.0-0' }}</span>
        </div>
        <div class="intel-item">
          <span class="label">Fear & Greed</span>
          <span class="value">{{ fearGreed }}</span>
        </div>
        <div class="intel-item">
          <span class="label">Signal Score</span>
          <span class="value">{{ signalScore }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .intel-panel {
      padding: 12px;
    }
    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--text-secondary);
    }
    .intel-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .intel-item {
      display: flex;
      justify-content: space-between;
      padding: 6px 8px;
      background: var(--bg-elevated, #0D1117);
      border-radius: 4px;
    }
    .label {
      font-size: 11px;
      color: var(--text-secondary);
    }
    .value {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary);
    }
  `],
})
export class MarketIntelPanelComponent implements OnInit {
  fundingRate = '--';
  openInterest = 0;
  fearGreed = '--';
  signalScore = '--';

  constructor(private intelApi: IntelligenceApiService) {}

  ngOnInit(): void {
    // TODO: Connect to WebSocket service for real-time updates
  }
}