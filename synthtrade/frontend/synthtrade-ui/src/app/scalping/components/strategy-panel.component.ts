/**
 * Strategy Panel Component
 * Shows active strategy and parameters. Updated live by AI Supervisor decisions via WS.
 */

import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { NgForOf, NgIf, DecimalPipe, NgClass } from '@angular/common';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { ScalpingWsService, SupervisorDecision } from '../services/scalping-ws.service';
import { SessionApiService } from '../services/session-api.service';

export interface StrategyParams {
  ema_fast?: number;
  ema_slow?: number;
  rsi_period?: number;
  rsi_overbought?: number;
  rsi_oversold?: number;
  bb_period?: number;
  bb_std?: number;
  take_profit_pct?: number;
  stop_loss_pct?: number;
  [key: string]: number | undefined;
}

const STRATEGY_DEFAULTS: Record<string, { label: string; desc: string; params: StrategyParams }> = {
  ema_cross: {
    label: 'EMA Cross',
    desc: 'Incrocio EMA veloce/lenta con filtro volume',
    params: { ema_fast: 9, ema_slow: 21, take_profit_pct: 0.4, stop_loss_pct: 0.25 },
  },
  rsi_bollinger: {
    label: 'RSI con Bollinger',
    desc: 'RSI oversold/overbought con bande di Bollinger',
    params: { rsi_period: 14, rsi_oversold: 30, rsi_overbought: 70, bb_period: 20, bb_std: 2, take_profit_pct: 0.5, stop_loss_pct: 0.3 },
  },
  vwap_reversion: {
    label: 'VWAP Reversion',
    desc: 'Mean reversion al VWAP giornaliero',
    params: { take_profit_pct: 0.35, stop_loss_pct: 0.2 },
  },
  momentum_base: {
    label: 'Momentum Base',
    desc: 'Trend following con momentum indicators',
    params: { ema_fast: 12, ema_slow: 26, take_profit_pct: 0.6, stop_loss_pct: 0.35 },
  },
  scalping_v2: {
    label: 'Scalping',
    desc: 'Auto-select via AI Signal Intelligence',
    params: { ema_fast: 9, ema_slow: 21, take_profit_pct: 0.5, stop_loss_pct: 0.3 },
  },
  stoch_rsi_bb_squeeze: {
    label: 'Stoch RSI con Bollinger Bands Squeeze',
    desc: 'Bollinger Bands squeeze + StochRSI per breakout da volatilità',
    params: { rsi_period: 14, bb_period: 20, bb_std: 2, take_profit_pct: 0.5, stop_loss_pct: 0.3 },
  },
};

@Component({
  selector: 'app-strategy-panel',
  standalone: true,
  imports: [NgForOf, NgIf, DecimalPipe, NgClass],
  template: `
    <div class="strategy-panel">
      <div class="panel-header">
        <span class="panel-title">Strategy</span>
        <span class="ai-badge" *ngIf="lastAiUpdate">AI</span>
      </div>
      <div class="title-hr"></div>

      <div *ngIf="!strategy" class="empty-state">
        <span>Avvia una sessione per caricare la strategia</span>
      </div>

      <ng-container *ngIf="strategy">
        <div class="strategy-name">{{ strategy.label }}</div>
        <div class="strategy-desc">{{ strategy.desc }}</div>

        <div class="params-grid">
          <div class="param-row" *ngFor="let key of numericParamKeys()">
            <span class="param-label">{{ formatParam(key) }}</span>
            <span class="param-value" [ngClass]="{'highlight': highlightedKeys.has(key)}">
              {{ strategy.params[key] | number:'1.0-4' }}
              <span *ngIf="key.endsWith('_pct') || key.endsWith('_percent')" class="unit">%</span>
            </span>
          </div>
        </div>

        <div *ngIf="lastAiUpdate" class="ai-note">
          <span class="ai-icon">🤖</span>
          <span>AI aggiornato · {{ lastAiUpdate }}</span>
        </div>
      </ng-container>
    </div>
  `,
  styles: [`
    .strategy-panel { padding: 16px; display: flex; flex-direction: column; gap: 12px; height: 100%; }

    .panel-title {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .title-hr { height: 1px; background: rgba(234,236,239,0.08); margin: -6px 0 12px 0; }

    .panel-header { display: flex; align-items: center; justify-content: space-between; }
    h3 { margin: 0; font-size: 13px; color: var(--text-secondary); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .ai-badge {
      font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 10px;
      background: rgba(240,185,11,0.15); color: #F0B90B; border: 1px solid rgba(240,185,11,0.3);
    }

    .empty-state {
      flex: 1; display: flex; align-items: center; justify-content: center;
      color: var(--text-secondary); font-size: 12px; text-align: center; opacity: 0.6;
    }

    .strategy-name {
      font-size: 16px; font-weight: 700; color: var(--accent-primary, #F0B90B);
    }
    .strategy-desc {
      font-size: 11px; color: var(--text-secondary); line-height: 1.4;
    }

    .params-grid { display: flex; flex-direction: column; gap: 4px; }
    .param-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 5px 8px; border-radius: 5px;
      background: rgba(255,255,255,0.03);
      transition: background 0.2s;
    }
    .param-row:hover { background: rgba(255,255,255,0.06); }
    .param-label { font-size: 11px; color: var(--text-secondary); text-transform: capitalize; }
    .param-value {
      font-size: 12px; font-weight: 600; color: var(--text-primary);
      font-variant-numeric: tabular-nums;
      transition: color 0.4s;
    }
    .param-value.highlight { color: #F0B90B; }
    .unit { font-size: 10px; opacity: 0.6; margin-left: 1px; }

    .ai-note {
      display: flex; align-items: center; gap: 6px;
      font-size: 10px; color: var(--text-secondary);
      border-top: 1px solid rgba(255,255,255,0.05);
      padding-top: 8px;
    }
    .ai-icon { font-size: 12px; }
  `],
})
export class StrategyPanelComponent implements OnInit, OnDestroy {
  strategy: { label: string; desc: string; params: StrategyParams } | null = null;
  lastAiUpdate: string | null = null;
  highlightedKeys: Set<string> = new Set();

  private sub?: Subscription;
  private sessionSub?: Subscription;

  constructor(
    private ws: ScalpingWsService,
    private sessionApi: SessionApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Load strategy from current session reactively
    this.sessionSub = this.sessionApi.session$.subscribe((session) => {
      if (session && session.status !== 'idle' && session.strategy) {
        this._loadStrategy(session.strategy);
      } else {
        this.strategy = null;
      }
      this.cdr.detectChanges();
    });

    // Listen for AI Supervisor decisions
    this.sub = this.ws.supervisorDecision$.pipe(
      filter(decision => decision !== null)
    ).subscribe((decision: SupervisorDecision) => {
      if (decision.new_strategy && STRATEGY_DEFAULTS[decision.new_strategy]) {
        this.strategy = { ...STRATEGY_DEFAULTS[decision.new_strategy] };
        this.highlightedKeys = new Set(Object.keys(this.strategy.params));
      }
      if (decision.new_params && this.strategy) {
        const updated = decision.new_params as Record<string, number>;
        this.highlightedKeys = new Set(Object.keys(updated));
        this.strategy.params = { ...this.strategy.params, ...updated };
        setTimeout(() => { this.highlightedKeys = new Set(); this.cdr.detectChanges(); }, 2000);
      }
      if (decision.action !== 'no_action') {
        const now = new Date();
        this.lastAiUpdate = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
      }
      this.cdr.detectChanges();
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.sessionSub?.unsubscribe();
  }

  private _loadStrategy(strategyKey: string): void {
    const def = STRATEGY_DEFAULTS[strategyKey] ?? STRATEGY_DEFAULTS['scalping_v2'];
    this.strategy = { ...def };
    this.cdr.detectChanges();
  }

  paramKeys(): string[] {
    return this.strategy ? Object.keys(this.strategy.params) : [];
  }

  numericParamKeys(): string[] {
    if (!this.strategy) return [];
    return Object.keys(this.strategy.params).filter(
      key => typeof this.strategy!.params[key] === 'number'
    );
  }

  formatParam(key: string): string {
    return key.replace(/_/g, ' ').replace('pct', '%').replace('_percent', '%');
  }
}