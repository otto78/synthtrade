/**
 * Strategy Panel Component
 * Displays active strategy and parameters
 */

import { Component, OnInit } from '@angular/core';
import { NgForOf, NgIf } from '@angular/common';
import { ScalpingWsService } from '../services/scalping-ws.service';

export interface StrategyParams {
  ema_fast?: number;
  ema_slow?: number;
  rsi_period?: number;
  bb_std?: number;
  take_profit_pct?: number;
  stop_loss_pct?: number;
  [key: string]: number | undefined;
}

export interface ActiveStrategy {
  name: string;
  type: string;
  params: StrategyParams;
  enabled: boolean;
}

@Component({
  selector: 'app-strategy-panel',
  standalone: true,
  imports: [NgForOf, NgIf],
  template: `
    <div class="strategy-panel">
      <h3>Strategy</h3>

      <div *ngIf="!strategy" class="no-strategy">No strategy loaded</div>

      <div *ngIf="strategy" class="strategy-info">
        <div class="name">{{ strategy.name }}</div>
        <div class="type">{{ strategy.type }}</div>

        <div class="params" *ngIf="strategy.params">
          <div class="param" *ngFor="let key of objectKeys(strategy.params)">
            <span class="param-label">{{ formatParam(key) }}</span>
            <span class="param-value">{{ strategy.params[key] }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .strategy-panel { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .no-strategy { color: var(--text-secondary); font-size: 12px; }
    .strategy-info { font-size: 12px; }
    .name { font-weight: 600; color: var(--accent-primary, #F0B90B); margin-bottom: 4px; }
    .type { color: var(--text-secondary); font-size: 11px; margin-bottom: 8px; }
    .params { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
    .param { display: flex; justify-content: space-between; padding: 4px 6px; background: var(--bg-elevated); border-radius: 4px; }
    .param-label { color: var(--text-secondary); text-transform: capitalize; }
    .param-value { color: var(--text-primary); font-weight: 500; }
  `],
})
export class StrategyPanelComponent implements OnInit {
  strategy?: ActiveStrategy;
  objectKeys = Object.keys;

  constructor(private ws: ScalpingWsService) {}

  ngOnInit(): void {
    // Default strategy for now - will be updated via WS when supervisor changes
    this.strategy = {
      name: 'Scalping v2.0',
      type: 'EMA Cross + Signal Intelligence',
      params: {
        ema_fast: 9,
        ema_slow: 21,
        take_profit_pct: 0.5,
        stop_loss_pct: 0.3
      },
      enabled: true
    };
  }

  formatParam(key: string): string {
    return key.replace(/_/g, ' ');
  }
}