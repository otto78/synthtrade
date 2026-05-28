/**
 * Scalping WebSocket Service
 * Real-time connection to scalping backend
 */

import { Injectable, OnDestroy } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subject, timer } from 'rxjs';
import { retryWhen, delayWhen } from 'rxjs/operators';

// Event types matching backend
export type ScalpingEventType =
  | 'candle'
  | 'signal'
  | 'order'
  | 'position'
  | 'supervisor'
  | 'risk_block'
  | 'trade_closed'
  | 'position_update'
  | 'intelligence';

export interface TradeClosedEvent {
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  timestamp: string;
}

export interface IntelligenceEvent {
  symbol: string;
  signal_score?: number;
  signal_bias?: 'bullish' | 'bearish' | 'neutral';
  tradeable?: boolean;
  confidence?: number;
  funding_rate?: number;
  open_interest?: number;
  fear_greed_value?: number;
  fear_greed_label?: string;
  cvd_trend?: string;
  long_pct?: number;
  short_pct?: number;
  recorded_at: string;
}

export interface ScalpingEvent {
  type: ScalpingEventType;
  payload: CandleEvent | SignalEvent | PositionEvent | SupervisorDecision | RiskBlockEvent | TradeClosedEvent | IntelligenceEvent;
  timestamp: string;
}

// Specific payload types
export interface CandleEvent {
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

export interface SignalEvent {
  symbol: string;
  type: 'BUY' | 'SELL';
  price: number;
  confidence: number;
  reason: string;
}

export interface PositionEvent {
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
}

/** Strategy parameter values — extensible for different strategy types */
export interface StrategyParams {
  /** Bollinger Bands period */
  bb_period?: number;
  /** Bollinger Bands standard deviation multiplier */
  bb_std?: number;
  /** RSI period */
  rsi_period?: number;
  /** RSI overbought threshold */
  rsi_overbought?: number;
  /** RSI oversold threshold */
  rsi_oversold?: number;
  /** EMA fast period */
  ema_fast?: number;
  /** EMA slow period */
  ema_slow?: number;
  /** Take-profit in percentage */
  take_profit_pct?: number;
  /** Stop-loss in percentage */
  stop_loss_pct?: number;
  /** Position size in quote currency */
  position_size?: number;
  /** Maximum concurrent positions */
  max_positions?: number;
  /** Additional strategy-specific parameters */
  [key: string]: unknown;
}

export interface SupervisorDecision {
  action: 'update_params' | 'change_strategy' | 'pause_trading' | 'resume_trading' | 'no_action';
  reason: string;
  confidence: number;
  new_params?: StrategyParams;
  new_strategy?: string;
  market_bias?: string;
  primary_signal?: string;
  decided_at?: string;
  timestamp?: string;
}

export interface RiskBlockEvent {
  symbol: string;
  blocked: boolean;
  reason: string;
}

@Injectable({
  providedIn: 'root',
})
export class ScalpingWsService implements OnDestroy {
  private ws$!: WebSocketSubject<ScalpingEvent>;
  /**
   * WS endpoint mounted at /ws/scalping in backend main.py.
   * This matches the /ws proxy rule in proxy.conf.json which handles WS upgrade
   * reliably. Use relative URL so it works through proxy AND direct connection.
   */
  private readonly WS_PATH = '/ws/scalping';
  private get _wsUrl(): string {
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    // When running standalone (no proxy), connect to backend directly.
    // When running via ng serve proxy, the proxy handles WS upgrade on /api/*.
    return `${proto}//${loc.host}${this.WS_PATH}`;
  }

  // Subjects per ogni tipo evento
  candle$ = new Subject<CandleEvent>();
  signal$ = new Subject<SignalEvent>();
  position$ = new Subject<PositionEvent>();
  supervisorDecision$ = new Subject<SupervisorDecision>();
  riskBlock$ = new Subject<RiskBlockEvent>();
  tradeClosed$ = new Subject<TradeClosedEvent>();
  intelligence$ = new Subject<IntelligenceEvent>();

  private connected = false;

  connect(): void {
    if (this.connected) return;

    this.ws$ = webSocket<ScalpingEvent>(this._wsUrl);

    this.ws$
      .pipe(
        retryWhen((errors) =>
          errors.pipe(
            delayWhen((_) => timer(3000))
            // Retry indefinitely instead of take(5)
          )
        )
      )
      .subscribe({
        next: (event) => this._dispatch(event),
        error: (err) => console.error('Scalping WS error:', err),
      });

    this.connected = true;
  }

  disconnect(): void {
    if (this.ws$) {
      this.ws$.complete();
      this.connected = false;
    }
  }

  private _dispatch(event: ScalpingEvent): void {
    switch (event.type) {
      case 'candle':
        this.candle$.next(event.payload as CandleEvent);
        break;
      case 'signal':
        this.signal$.next(event.payload as SignalEvent);
        break;
      case 'position':
      case 'position_update':
        this.position$.next(event.payload as PositionEvent);
        break;
      case 'supervisor':
        this.supervisorDecision$.next(event.payload as SupervisorDecision);
        break;
      case 'risk_block':
        this.riskBlock$.next(event.payload as RiskBlockEvent);
        break;
      case 'trade_closed':
        this.tradeClosed$.next(event.payload as TradeClosedEvent);
        break;
      case 'intelligence':
        this.intelligence$.next(event.payload as IntelligenceEvent);
        break;
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}