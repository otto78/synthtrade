/**
 * Market Intelligence Panel Component
 */

import { Component, OnInit } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { IntelligenceApiService } from '../services/intelligence-api.service';

@Component({
  selector: 'app-market-intel-panel',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <div class="intel-panel">
      <h3>Market Intelligence</h3>
      <div class="intel-grid">
        <div class="intel-item"><span class="label">Funding Rate</span><span class="value">{{ fundingRate }}%</span></div>
        <div class="intel-item"><span class="label">Open Interest</span><span class="value">{{ openInterest | number:'1.0-0' }}</span></div>
        <div class="intel-item"><span class="label">Fear & Greed</span><span class="value">{{ fearGreed }}</span></div>
        <div class="intel-item"><span class="label">Signal Score</span><span class="value">{{ signalScore }}</span></div>
      </div>
    </div>
  `,
  styles: [`
    .intel-panel { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .intel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .intel-item { display: flex; justify-content: space-between; padding: 6px 8px; background: var(--bg-elevated); border-radius: 4px; }
    .label { font-size: 11px; color: var(--text-secondary); }
    .value { font-size: 12px; font-weight: 600; color: var(--text-primary); }
  `],
})
export class MarketIntelPanelComponent implements OnInit {
  fundingRate = '--';
  openInterest = 0;
  fearGreed = '--';
  signalScore = '--';

  constructor(private intelApi: IntelligenceApiService) {}

  ngOnInit(): void {
    this.loadSnapshot('BTCUSDT');
  }

  private loadSnapshot(symbol: string): void {
    this.intelApi.getLatestSnapshot(symbol).subscribe({
      next: (data) => {
        console.log('Intelligence data:', data); // Debug
        // Backend restituisce valori semplici: funding_rate (number), open_interest (number), signal_score (number)
        if (data && typeof data === 'object') {
          // Funding rate - può essere numero o dettagliato
          if (typeof data.funding_rate === 'number') {
            this.fundingRate = data.funding_rate.toFixed(4);
          } else if (data.funding_rate !== undefined && data.funding_rate !== null) {
            this.fundingRate = String(data.funding_rate);
          }

          // Open interest - può essere numero o dettagliato
          if (typeof data.open_interest === 'number') {
            this.openInterest = data.open_interest;
          }

          // Fear & Greed
          if (data.fear_greed && typeof data.fear_greed === 'object' && data.fear_greed.label) {
            this.fearGreed = data.fear_greed.label;
          }

          // Signal score
          if (typeof data.signal_score === 'number') {
            this.signalScore = data.signal_score.toString();
          }
        }
      },
      error: (err) => {
        console.error('Intelligence load error:', err);
      }
    });
  }
}