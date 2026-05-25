/**
 * Market Intelligence Panel Component
 * Connected to WebSocket service
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { AsyncPipe, DecimalPipe } from '@angular/common';
import { ScalpingWsService, MarketIntelSnapshot } from '../services/scalping-ws.service';
import { Subscription } from 'rxjs';

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
export class MarketIntelPanelComponent implements OnInit, OnDestroy {
  fundingRate = '--';
  openInterest = 0;
  fearGreed = '--';
  signalScore = '--';

  private sub = new Subscription();

  constructor(private wsService: ScalpingWsService) {}

  ngOnInit(): void {
    // Connect to WebSocket
    this.wsService.connect();

    // TODO: Subscribe to intelligence snapshots when backend sends them
    // this.sub.add(this.wsService.marketIntel$.subscribe(snapshot => this.update(snapshot)));
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }
}