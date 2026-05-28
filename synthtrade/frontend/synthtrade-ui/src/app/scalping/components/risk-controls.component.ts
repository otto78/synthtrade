/**
 * Risk Controls Component
 * Displays and modifies risk manager configuration
 */

import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIf } from '@angular/common';
import { HttpClient } from '@angular/common/http';

export interface RiskConfig {
  max_position_size: number;
  max_daily_loss: number;
  max_drawdown: number;
  leverage: number;
  stop_loss_pct: number;
  take_profit_pct: number;
}

@Component({
  selector: 'app-risk-controls',
  standalone: true,
  imports: [FormsModule, NgIf],
  template: `
    <div class="risk-controls">
      <h3>Risk Controls</h3>

      <div *ngIf="!config" class="loading">Loading...</div>

      <div *ngIf="config" class="risk-form">
        <div class="field">
          <label>Max Position Size ($)</label>
          <input type="number" [(ngModel)]="config.max_position_size" />
        </div>

        <div class="field">
          <label>Max Daily Loss ($)</label>
          <input type="number" [(ngModel)]="config.max_daily_loss" />
        </div>

        <div class="field">
          <label>Max Drawdown (%)</label>
          <input type="number" step="0.1" [(ngModel)]="config.max_drawdown" />
        </div>

        <div class="field">
          <label>Leverage</label>
          <input type="number" [(ngModel)]="config.leverage" />
        </div>

        <div class="field">
          <label>Stop Loss (%)</label>
          <input type="number" step="0.1" [(ngModel)]="config.stop_loss_pct" />
        </div>

        <div class="field">
          <label>Take Profit (%)</label>
          <input type="number" step="0.1" [(ngModel)]="config.take_profit_pct" />
        </div>

        <button class="btn-save" (click)="saveConfig()">Save Config</button>
      </div>
    </div>
  `,
  styles: [`
    .risk-controls { padding: 12px; }
    h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--text-secondary); }
    .loading { color: var(--text-secondary); font-size: 12px; }
    .risk-form { font-size: 12px; }
    .field { margin-bottom: 10px; }
    label { display: block; color: var(--text-secondary); margin-bottom: 4px; }
    input { width: 100%; padding: 6px 8px; border-radius: 4px; border: 1px solid var(--border-default); background: var(--bg-elevated); color: var(--text-primary); font-size: 12px; }
    .btn-save { width: 100%; padding: 8px; border-radius: 4px; background: var(--accent-primary, #F0B90B); color: #000; border: none; font-weight: 600; cursor: pointer; }
  `],
})
export class RiskControlsComponent implements OnInit {
  config?: RiskConfig;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http.get<RiskConfig>('/api/scalping/risk/config').subscribe({
      next: (cfg) => {
        if (Object.keys(cfg).length > 0) {
          this.config = cfg;
        } else {
          this.loadDefaultConfig();
        }
      },
      error: () => this.loadDefaultConfig()
    });
  }

  private loadDefaultConfig() {
    this.config = {
      max_position_size: 100,
      max_daily_loss: 50,
      max_drawdown: 10,
      leverage: 10,
      stop_loss_pct: 0.3,
      take_profit_pct: 0.5
    };
  }

  saveConfig(): void {
    if (!this.config) return;
    this.http.post<RiskConfig>('/api/scalping/risk/config', this.config).subscribe({
      next: () => {},
      error: (err: Error) => console.error('Failed to save risk config', err)
    });
  }
}