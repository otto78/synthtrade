/**
 * Scalping WebSocket Service
 * Real-time connection to scalping backend
 */

import { Injectable, OnDestroy } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subject, BehaviorSubject, timer, defer } from 'rxjs';
import { retryWhen, delayWhen, tap } from 'rxjs/operators';
import { ScalpingSession } from '../models/session.model';

export type WsConnectionStatus = 'connected' | 'connecting' | 'disconnected';

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
  | 'intelligence'
  | 'session_restored'
  | 'error';

export interface TradeClosedEvent {
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  timestamp: string;
  signal_reason?: string;
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

 export interface ErrorEventPayload {
   code: string;
   message: string;
 }

 // Specific payload types

export interface ScalpingEvent {
  type: ScalpingEventType;
  payload:
    | CandleEvent
    | SignalEvent
    | PositionEvent
    | SupervisorDecision
    | RiskBlockEvent
    | TradeClosedEvent
    | IntelligenceEvent
    | ErrorEventPayload
    | ScalpingSession;
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
  entry_time?: string;
  pnl: number;
  pnl_pct: number;
  quantity?: number;
  trade_value_usd?: number;
  stop_loss_price?: number;
  take_profit_price?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
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
  /** TASK-911: Whether the decision was actually applied (false = blocked by guard) */
  was_applied?: boolean;
  /** TASK-911: Reason why the decision was blocked (e.g. cooldown, resume guard) */
  blocked_reason?: string;
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
  private ws$: WebSocketSubject<ScalpingEvent> | null = null;
  private _reconnectAttempt = 0;
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

  // BehaviorSubjects for automatic replay when reconnecting
  candle$ = new BehaviorSubject<CandleEvent | null>(null);
  signal$ = new BehaviorSubject<SignalEvent | null>(null);
  position$ = new BehaviorSubject<PositionEvent | null>(null);
  supervisorDecision$ = new BehaviorSubject<SupervisorDecision | null>(null);
  riskBlock$ = new BehaviorSubject<RiskBlockEvent | null>(null);
  tradeClosed$ = new Subject<TradeClosedEvent>();  // Keep as Subject (one-time events)
  intelligence$ = new BehaviorSubject<IntelligenceEvent | null>(null);
  /** Backend errors (e.g. live trade failed, insufficient funds) */
  error$ = new Subject<ErrorEventPayload>();
  /** Session updates (balance, status changes) */
  sessionRestored$ = new Subject<ScalpingSession>();

  /** Stato connessione WS — usato per mostrare banner 'Reconnecting...' in UI */
  connectionStatus$ = new BehaviorSubject<WsConnectionStatus>('disconnected');

  private connected = false;

  /** Ritorna true se il WS è attualmente connesso */
  isConnected(): boolean {
    return this.connectionStatus$.getValue() === 'connected';
  }

  connect(): void {
    if (this.connected) return;
    this._reconnectAttempt = 0;

    // Using defer() ensures a NEW WebSocketSubject is created on each subscription,
    // which is necessary because WebSocketSubject cannot be reused after disconnect.
    // Without this, retryWhen resubscribes to the same errored Subject and never
    // actually opens a new WebSocket connection.
    const wsFactory = () => {
      this.ws$ = webSocket<ScalpingEvent>(this._wsUrl);
      return this.ws$;
    };

    defer(wsFactory)
      .pipe(
        retryWhen((errors) =>
          errors.pipe(
            tap(() => {
              this._reconnectAttempt++;
              this.connectionStatus$.next('connecting');
              console.log(`Scalping WS reconnecting (attempt ${this._reconnectAttempt})...`);
            }),
            delayWhen((_) => timer(this._reconnectAttempt > 5 ? 10000 : 3000))
          )
        )
      )
      .subscribe({
        next: (event) => {
          if (this.connectionStatus$.getValue() !== 'connected') {
            this.connectionStatus$.next('connected');
          }
          this._dispatch(event);
        },
        error: (err) => {
          this.connectionStatus$.next('disconnected');
          console.error('Scalping WS error:', err);
        },
        complete: () => {
          this.connected = false;
          this.connectionStatus$.next('disconnected');
          console.log('Scalping WS completed');
        },
      });

    this.connectionStatus$.next('connecting');
    this.connected = true;
  }

  disconnect(): void {
    if (this.ws$) {
      this.ws$.complete();
      this.ws$ = null;
      this.connected = false;
      this.connectionStatus$.next('disconnected');
    }
    // Don't reset BehaviorSubjects - keep last values for replay
  }

  private _dispatch(event: ScalpingEvent): void {
    switch (event.type) {
      case 'candle':
        this.candle$.next(event.payload as CandleEvent);
        break;
      case 'signal': {
        if (this.position$.getValue()) {
          return;
        }
        this.signal$.next(event.payload as SignalEvent);
        break;
      }
      case 'position':
      case 'position_update':
        this.signal$.next(null);
        this.position$.next(event.payload as PositionEvent);
        break;
      case 'supervisor':
        this.supervisorDecision$.next(event.payload as SupervisorDecision);
        break;
      case 'risk_block':
        this.riskBlock$.next(event.payload as RiskBlockEvent);
        break;
      case 'trade_closed':
        this.position$.next(null);
        this.tradeClosed$.next(event.payload as TradeClosedEvent);
        break;
      case 'intelligence':
        this.intelligence$.next(event.payload as IntelligenceEvent);
        break;
      case 'session_restored':
        this.sessionRestored$.next(event.payload as ScalpingSession);
        break;
      case 'error':
        this.error$.next(event.payload as ErrorEventPayload);
        break;
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
